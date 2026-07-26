import os
import json
import threading
import time
import tkinter as tk
from tkinter import ttk, messagebox
from config import FILE_SIGNATURES, APP_NAME
from carver import scan_disk_worker


class ScanMixin:
    def get_active_signatures(self):
        selected_cats = [cat for cat, var in getattr(self, "category_vars", {}).items() if var.get()]
        if not selected_cats:
            # If nothing is selected, default to all to avoid scanning nothing
            selected_cats = list(getattr(self, "category_vars", {}).keys())
        return [sig for sig in FILE_SIGNATURES.values() if sig["category"] in selected_cats]

    def parse_block_ranges(self, range_str, total_size):
        intervals = []
        if not range_str:
            return [(0, total_size)]
            
        parts = range_str.split(",")
        for part in parts:
            part = part.strip()
            if not part:
                continue
            try:
                if "-" in part:
                    s_part, e_part = part.split("-", 1)
                    start_block = int(s_part.strip())
                    end_block = int(e_part.strip())
                else:
                    start_block = int(part)
                    end_block = start_block
                    
                start_block = max(1, min(100, start_block))
                end_block = max(start_block, min(100, end_block))
                
                start_offset = int((start_block - 1) * (total_size / 100))
                end_offset = int(end_block * (total_size / 100))
                
                # Align to 512-byte sector boundary for raw disk reading
                start_offset = (start_offset // 512) * 512
                end_offset = (end_offset // 512) * 512
                
                intervals.append((start_offset, end_offset))
            except Exception as ex:
                print(f"Error parsing part '{part}': {ex}")
                
        if not intervals:
            return [(0, total_size)]
            
        intervals.sort(key=lambda x: x[0])
        merged = []
        for start, end in intervals:
            if not merged:
                merged.append((start, end))
            else:
                prev_start, prev_end = merged[-1]
                if start <= prev_end:
                    merged[-1] = (prev_start, max(prev_end, end))
                else:
                    merged.append((start, end))
        return merged

    def start_recovery(self):
        # 0. Check if there's an active/paused session
        if getattr(self, "is_scanning", False):
            selected_disp = self.drive_var.get()
            target_drive = self.drives_map.get(selected_disp)
            if target_drive and target_drive == self.active_drive:
                self.resume_recovery()
                return
            
            if not messagebox.askyesno("Yeni Tarama Başlat", "Aktif bir tarama seansınız bulunuyor. Yeni bir tarama başlatmak mevcut seansı durduracaktır. Devam etmek istiyor musunuz?"):
                return
            self.is_scanning = False
            self.scan_paused = False
            time.sleep(0.3)
            self.current_session_file = None
        elif getattr(self, "current_session_file", None) is not None:
            if not messagebox.askyesno("Yeni Tarama Başlat", "Yüklü veya duraklatılmış bir seansınız bulunuyor. Yeni bir tarama seansı başlatmak mevcut seansı kapatacaktır. Devam etmek istiyor musunuz?"):
                return
            self.current_session_file = None
            
        selected_disp = self.drive_var.get()
        if not selected_disp and hasattr(self, "drive_combo") and self.drive_combo.get():
            selected_disp = self.drive_combo.get()
            self.drive_var.set(selected_disp)
            
        if not selected_disp or selected_disp == "Diskler aranıyor...":
            if hasattr(self, "drives_map") and self.drives_map:
                selected_disp = list(self.drives_map.keys())[0]
                self.drive_var.set(selected_disp)
            else:
                messagebox.showwarning("Uyarı", "Lütfen kurtarma yapmak istediğiniz diski seçin!")
                return
            
        self.active_drive = self.drives_map.get(selected_disp)
        self.active_drive_size = self.drives_sizes_map.get(selected_disp, 0)
        
        if not self.active_drive and hasattr(self, "drives_map") and self.drives_map:
            # Fallback to first available drive
            first_disp = list(self.drives_map.keys())[0]
            self.active_drive = self.drives_map[first_disp]
            self.active_drive_size = self.drives_sizes_map.get(first_disp, 0)
            self.drive_var.set(first_disp)
            
        if not self.active_drive:
            messagebox.showerror("Hata", "Sürücü yolu tespit edilemedi.")
            return

        # Initialize recovery directory selection
        if not getattr(self, "current_session_file", None):
            ok = self.setup_new_session_flow()
            if not ok:
                # User cancelled or invalid selection
                self.is_scanning = False
                self.scan_paused = False
                self.start_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
                self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                return
                
        # Final safety check: double verify same-disk constraint
        if self.is_same_disk(self.active_drive, self.selected_output_dir):
            suggested_root = self.get_default_target_drive_root()
            if suggested_root:
                self.selected_output_dir = os.path.abspath(os.path.join(suggested_root, "kurtarilan_dosyalar"))
                if hasattr(self, "path_lbl") and self.path_lbl:
                    self.path_lbl.config(text=self.selected_output_dir)
                if hasattr(self, "update_target_drive_status"):
                    self.update_target_drive_status()
            
            # Re-check after auto-fixing
            if self.is_same_disk(self.active_drive, self.selected_output_dir):
                messagebox.showerror(
                    "Kritik Hata: Aynı Disk!", 
                    "Hata: Kurtarma yapmak istediğiniz hedef disk ile kaynak disk aynı fiziksel disk üzerindedir!\n\n"
                    "Verilerin üst üste yazılmasını (overwrite) önlemek için lütfen kurtarma konumunu farklı bir diske ayarlayın."
                )
                self.is_scanning = False
                self.scan_paused = False
                self.start_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
                self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.current_session_file = None
                return

        active_sigs = self.get_active_signatures()

        self.is_scanning = True
        self.scan_paused = False
        
        self.start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.pause_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.stop_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        
        self.virtual_files.clear()
        self.tree_item_map.clear()
        self.file_tree.delete(*self.file_tree.get_children())
        self.reset_ui_counts()
        
        # Reset stats UI
        self.resume_offset = 0
        self.elapsed_seconds = 0.0
        drive_total_gb = (self.active_drive_size / (1024 * 1024 * 1024)) if self.active_drive_size > 0 else 0.0
        
        self.lbl_progress_val.config(text=f"%0.0 (0.00 GB / {drive_total_gb:.2f} GB)")
        if hasattr(self, "lbl_entire_progress_val") and self.lbl_entire_progress_val:
            self.lbl_entire_progress_val.config(text=f"%0.0 (0.00 GB / {drive_total_gb:.2f} GB)")
        if hasattr(self, "lbl_drive_scanned") and self.lbl_drive_scanned:
            self.lbl_drive_scanned.config(text="Taranan Alan: 0.00 GB (%0.0)", fg="#0084FF")
            
        self.lbl_speed_val.config(text="0.00 MB/s")
        self.lbl_elapsed_val.config(text="00:00")
        self.lbl_eta_val.config(text="Hesaplanıyor...")
        
        self.progress_bar.config(mode="determinate", value=0)
        if hasattr(self, "entire_progress_bar") and self.entire_progress_bar:
            self.entire_progress_bar.config(mode="determinate", value=0)
        
        clean_disp_name = selected_disp.split(":")[1].strip() if ":" in selected_disp else selected_disp
        self.scan_header_lbl.config(text=f'"{clean_disp_name}" Taranıyor...')
        self.scan_progress_lbl.config(text="Tarama başlatıldı. Sektörler okunuyor...")
        
        if hasattr(self, "update_target_drive_status"):
            self.update_target_drive_status()
        
        # Helper function to parse values with comma/dot decimals and unit scaling
        def parse_to_bytes(val_str, unit):
            try:
                val_str = val_str.replace(",", ".")
                val = float(val_str)
                if unit == "MB":
                    return int(val * 1024 * 1024)
                elif unit == "GB":
                    return int(val * 1024 * 1024 * 1024)
                elif unit == "TB":
                    return int(val * 1024 * 1024 * 1024 * 1024)
            except:
                pass
            return None

        # Determine scanning boundaries
        target_intervals = [(0, self.active_drive_size)]
        if self.use_custom_range_var.get():
            target_intervals = self.parse_block_ranges(self.custom_block_range_var.get(), self.active_drive_size)
            self.scan_start_offset = target_intervals[0][0]
            self.scan_end_offset = target_intervals[-1][1]
        else:
            self.scan_start_offset = 0
            self.scan_end_offset = self.active_drive_size
            
        # Initialize parallel segments
        self.segment_lock = threading.Lock()
        self.segment_progress = {}
        
        if self.use_parallel_var.get():
            try:
                worker_count = int(self.worker_count_var.get())
                if worker_count < 1: worker_count = 1
                if worker_count > 16: worker_count = 16
            except:
                worker_count = 4
                
            try:
                segment_size_gb = float(self.segment_size_gb_var.get())
                if segment_size_gb <= 0: segment_size_gb = 100.0
            except:
                segment_size_gb = 100.0
                
            segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)
            self.scan_segments = []
            if not hasattr(self, "segment_bounds"):
                self.segment_bounds = {}
            
            for start_offset, end_offset in target_intervals:
                offset = start_offset
                while offset < end_offset:
                    end = min(offset + segment_size_bytes, end_offset)
                    self.scan_segments.append((offset, end))
                    self.segment_progress[offset] = 0
                    self.segment_bounds[offset] = end
                    offset = end
        else:
            worker_count = 1
            self.scan_segments = []
            for start_offset, end_offset in target_intervals:
                self.scan_segments.append((start_offset, end_offset))
                self.segment_progress[start_offset] = 0
                if not hasattr(self, "segment_bounds"):
                    self.segment_bounds = {}
                self.segment_bounds[start_offset] = end_offset
            
        self.active_worker_count = worker_count
        
        # Start the worker threads
        for _ in range(worker_count):
            threading.Thread(target=scan_disk_worker, name="ScanWorker", args=(self, self.active_drive, active_sigs), daemon=True).start()
            
        # Open dedicated live scan progress modal panel
        if hasattr(self, "show_scan_progress_modal"):
            self.after(100, self.show_scan_progress_modal)

    def pause_recovery(self):
        self.scan_paused = True
        self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.resume_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.backup_btn.config(state="normal", bg="#FF9F43", fg=self.text_white)
        self.status_lbl.config(text="Tarama duraklatıldı.")
        self.save_scan_state()

    def resume_recovery(self):
        self.scan_paused = False
        self.pause_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.status_lbl.config(text="Tarama devam ediyor...")
        self.last_auto_export_time = time.time() # Reset 5-minute timer
        if hasattr(self, "toggle_parallel_options"):
            self.toggle_parallel_options()
        self.ensure_worker_threads_running()
            
    def manual_backup(self):
        self.status_lbl.config(text="Seans kaydediliyor ve dosyalar yedekleniyor...")
        self.save_scan_state()
        self.auto_export_unexported()

    def ensure_worker_threads_running(self):
        # Check if threads are already running
        running = any(t.name == "ScanWorker" and t.is_alive() for t in threading.enumerate())
        if running:
            return
            
        active_sigs = self.get_active_signatures()
        
        self.scan_start_offset = getattr(self, "scan_start_offset", 0)
        self.scan_end_offset = getattr(self, "scan_end_offset", self.active_drive_size)
        
        if not getattr(self, "scan_segments", None) or getattr(self, "scan_paused", False):
            try:
                segment_size_gb = float(self.segment_size_gb_var.get())
            except:
                segment_size_gb = 100.0
            segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)
            
            target_intervals = []
            if getattr(self, "scan_queue", None):
                # Build target intervals from the scan queue in order
                for block_num in self.scan_queue:
                    start_offset = int((block_num - 1) * (self.active_drive_size / 100))
                    end_offset = int(block_num * (self.active_drive_size / 100))
                    start_offset = (start_offset // 512) * 512
                    end_offset = (end_offset // 512) * 512
                    target_intervals.append((start_offset, end_offset))
                self.scan_start_offset = min(x[0] for x in target_intervals) if target_intervals else 0
                self.scan_end_offset = max(x[1] for x in target_intervals) if target_intervals else self.active_drive_size
            elif self.use_custom_range_var.get():
                target_intervals = self.parse_block_ranges(self.custom_block_range_var.get(), self.active_drive_size)
                self.scan_start_offset = target_intervals[0][0]
                self.scan_end_offset = target_intervals[-1][1]
            else:
                target_intervals = [(0, self.active_drive_size)]
                self.scan_start_offset = 0
                self.scan_end_offset = self.active_drive_size
                
            if not getattr(self, "segment_progress", None):
                self.segment_progress = {}
            if not getattr(self, "segment_lock", None):
                self.segment_lock = threading.Lock()
                
            self.scan_segments = []
            
            # Always get unscanned intervals for each target interval to prevent scanning already scanned segments
            for start_offset, end_offset in target_intervals:
                unscanned_intervals = self.get_unscanned_segments(start_offset, end_offset)
                for u_start, u_end in unscanned_intervals:
                    offset = u_start
                    while offset < u_end:
                        end = min(offset + segment_size_bytes, u_end)
                        prog = self.segment_progress.get(offset, 0)
                        prog = (prog // 512) * 512  # Align to sector size for Windows seek protection
                        if prog < (end - offset):
                            self.scan_segments.append((offset, end))
                            if not hasattr(self, "segment_bounds"):
                                self.segment_bounds = {}
                            self.segment_bounds[offset] = end
                        offset = end
            
            if self.scan_from_end_var.get():
                self.scan_segments.reverse()
                
        if not getattr(self, "segment_progress", None):
            self.segment_progress = {}
        if not getattr(self, "segment_lock", None):
            self.segment_lock = threading.Lock()
            
        try:
            worker_count = int(self.worker_count_var.get()) if self.use_parallel_var.get() else 1
        except:
            worker_count = 4 if self.use_parallel_var.get() else 1
            
        self.active_worker_count = worker_count
        for _ in range(worker_count):
            threading.Thread(target=scan_disk_worker, name="ScanWorker", args=(self, self.active_drive, active_sigs), daemon=True).start()

    def stop_recovery(self):
        self.is_scanning = False
        self.scan_paused = False
        self.status_lbl.config(text="Durduruluyor...")
        self.save_scan_state()
        self.auto_export_unexported()

    def save_scan_state(self, force_synchronous=False, is_exit=False):
        if not self.active_drive:
            return
            
        import os
        import json
        import datetime
        
        # Ensure yedekler directory exists
        if not os.path.exists("yedekler"):
            os.makedirs("yedekler")
            
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        if not getattr(self, "current_session_file", None):
            # Create timestamped file if not defined yet
            session_dir = os.path.join("yedekler", f"oturum_{timestamp}")
            os.makedirs(session_dir, exist_ok=True)
            self.current_session_file = os.path.join(session_dir, f"session_{timestamp}.json")
            
        target_file = self.current_session_file
            
        # Safe copy of virtual files to prevent concurrent modification exceptions during background dump
        virtual_files_copy = [dict(f) for f in self.virtual_files]
            
        # Calculate statistics
        with self.segment_lock:
            total_scanned_bytes = sum(self.segment_progress.values()) if getattr(self, "segment_progress", None) else 0
            segment_progress_copy = dict(self.segment_progress) if getattr(self, "segment_progress", None) else {}
            
        range_size = (self.scan_end_offset - self.scan_start_offset) if getattr(self, "scan_start_offset", None) is not None else self.active_drive_size
        if range_size <= 0:
            range_size = self.active_drive_size
            
        scanned_gb = total_scanned_bytes / (1024*1024*1024)
        total_gb = range_size / (1024*1024*1024)
        scanned_percent = (total_scanned_bytes / range_size * 100) if range_size > 0 else 0.0
        elapsed_minutes = getattr(self, "elapsed_seconds", 0.0) / 60.0
        
        total_files = len(virtual_files_copy)
        exported_files = sum(1 for f in virtual_files_copy if f.get("exported", False))
        
        # Comprehensive list of files found with their details
        files_summary = [
            {
                "name": f["name"],
                "size_bytes": f["size"],
                "offset": f["offset"],
                "offset_mb": round(f["offset"] / (1024 * 1024), 2),
                "category": f["category"],
                "exported": f.get("exported", False),
                "custom_path": f.get("custom_path", "")
            }
            for f in virtual_files_copy
        ]
        
        # Get friendly names for auditing/matching
        source_name = self.get_friendly_name_of_drive(self.active_drive)
        target_name = self.get_friendly_name_of_target(self.selected_output_dir)
        
        state = {
            "timestamp": datetime.datetime.now().strftime("%d.%m.%Y %H:%M:%S"),
            "kaynak_disk_adi": source_name,
            "hedef_disk_adi": target_name,
            "kaynak_disk": self.active_drive,
            "hedef_disk": self.selected_output_dir,
            "toplam_gb": round(total_gb, 4),
            "tamamlanan_gb": round(scanned_gb, 4),
            "ilerleme_yuzdesi": round(scanned_percent, 2),
            "toplam_kurtarilan_dosya": total_files,
            "aktarilan_dosya_sayisi": exported_files,
            "gecen_sure_dakika": round(elapsed_minutes, 2),
            
            "active_drive": self.active_drive,
            "active_drive_size": self.active_drive_size,
            "resume_offset": getattr(self, "resume_offset", 0),
            "virtual_files": virtual_files_copy,
            "elapsed_seconds": getattr(self, "elapsed_seconds", 0.0),
            "scan_source": getattr(self, "scan_source", "dashboard"),
            "selected_output_dir": self.selected_output_dir,
            "use_parallel": self.use_parallel_var.get(),
            "worker_count": self.worker_count_var.get(),
            "segment_size_gb": self.segment_size_gb_var.get(),
            "search_unscanned": self.search_unscanned_var.get(),
            "scan_from_end": self.scan_from_end_var.get(),
            "segment_progress": segment_progress_copy,
            "segment_bounds": getattr(self, "segment_bounds", {}),
            "ntfs_deleted_files": getattr(self, "ntfs_deleted_files", {}),
            "block_copy_counts": getattr(self, "block_copy_counts", [0] * 100),
            "block_unwanted_counts": getattr(self, "block_unwanted_counts", [0] * 100),
            "use_custom_range": self.use_custom_range_var.get(),
            "custom_block_range": self.custom_block_range_var.get(),
            "custom_start": self.custom_start_var.get(),
            "custom_end": self.custom_end_var.get(),
            "custom_unit": self.custom_unit_var.get(),
            "scan_start_offset": getattr(self, "scan_start_offset", 0),
            "scan_end_offset": getattr(self, "scan_end_offset", self.active_drive_size),
            
            # User Audit Details
            "total_bytes": range_size,
            "scanned_bytes": total_scanned_bytes,
            "scanned_gb": round(scanned_gb, 4),
            "total_gb": round(total_gb, 4),
            "scanned_percent": round(scanned_percent, 2),
            "elapsed_minutes": round(elapsed_minutes, 2),
            "total_files_found": total_files,
            "exported_files_count": exported_files,
            "files_summary": files_summary,
            "is_exit": is_exit
        }
        # Determine the user output session directory
        user_session_dir = None
        if getattr(self, "selected_output_dir", None):
            base_name = os.path.basename(target_file)
            name_no_ext = os.path.splitext(base_name)[0]
            session_folder = name_no_ext.replace("session_", "oturum_")
            user_session_dir = os.path.join(self.selected_output_dir, session_folder)

        # Update status labels to show backup is in progress
        self.status_lbl.config(text="Otomatik yedek alınıyor...")
        if hasattr(self, "gallery_status_lbl") and self.gallery_status_lbl:
            self.gallery_status_lbl.config(text="Otomatik yedek alınıyor...")
            
        # Run JSON dumping and disk writing
        def do_save():
            try:
                # 1. Write internal session file
                with open(target_file, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=4)
                
                # 2. Write duplicate to selected output directory if available
                if user_session_dir:
                    os.makedirs(user_session_dir, exist_ok=True)
                    user_target_file = os.path.join(user_session_dir, os.path.basename(target_file))
                    with open(user_target_file, "w", encoding="utf-8") as f:
                        json.dump(state, f, indent=4)
                    
                # Write a clean text file containing the offsets map for easy manual inspections
                session_dir = os.path.dirname(target_file)
                report_file = os.path.join(session_dir, "kurtarma_haritasi_ve_ofsetler.txt")
                
                # Build the report string
                report_lines = []
                report_lines.append(f"{APP_NAME} Kurtarma Raporu ve Ofset Haritasi\n")
                report_lines.append("============================================================================================================================\n")
                report_lines.append(f"Tarih/Saat: {state['timestamp']}\n")
                report_lines.append(f"Kaynak Disk: {state['kaynak_disk_adi']}\n")
                report_lines.append(f"Toplam Bulunan Dosya: {len(state['virtual_files'])}\n")
                report_lines.append("============================================================================================================================\n")
                report_lines.append(f"{'Dosya Adi':<45} | {'Boyut':<12} | {'Disk Ofseti (Byte)':<20} | {'Disk Ofseti (MB)':<18} | {'Durum':<12}\n")
                report_lines.append("----------------------------------------------------------------------------------------------------------------------------\n")
                for vf in state["virtual_files"]:
                    name = vf["name"]
                    if len(name) > 43:
                        name = name[:40] + "..."
                    size_str = self.format_size(vf["size"])
                    offset = vf["offset"]
                    offset_mb = offset / (1024 * 1024)
                    status_str = "Kaydedildi" if vf.get("exported", False) else "Kaydedilmedi"
                    report_lines.append(f"{name:<45} | {size_str:<12} | {offset:<20} | {offset_mb:.2f} MB | {status_str:<12}\n")
                
                report_content = "".join(report_lines)
                
                # Write internal text report
                with open(report_file, "w", encoding="utf-8") as rf:
                    rf.write(report_content)
                    
                # Write duplicate text report to selected output directory if available
                if user_session_dir:
                    user_report_file = os.path.join(user_session_dir, "kurtarma_haritasi_ve_ofsetler.txt")
                    with open(user_report_file, "w", encoding="utf-8") as urf:
                        urf.write(report_content)
                        
                try:
                    self.auto_export_unexported()
                except Exception as ex:
                    print(f"Otomatik aktarım tetikleme hatası: {ex}")
                    
                self.msg_queue.put(("save_state_success", None))
            except Exception as e:
                print(f"Durum kaydedilemedi: {e}")
                
        if force_synchronous:
            do_save()
        else:
            threading.Thread(target=do_save, daemon=True).start()

    def close_current_session(self):
        if not getattr(self, "current_session_file", None):
            return
            
        confirm = messagebox.askyesno(
            "Oturumu Kapat", 
            "Mevcut tarama oturumunu kapatmak istediğinizden emin misiniz?\n\n"
            "Oturum durumunuz kaydedilecek ve listelenen dosyalar temizlenecektir."
        )
        if not confirm:
            return
            
        # Save state if scanning or has active drive
        if self.active_drive:
            self.save_scan_state()
            
        # Clear active state
        self.is_scanning = False
        self.scan_paused = False
        self.current_session_file = None
        self.active_drive = None
        self.active_drive_size = 0
        self.resume_offset = 0
        self.elapsed_seconds = 0.0
        self.virtual_files.clear()
        self.segment_progress.clear()
        if hasattr(self, "segment_bounds"):
            self.segment_bounds.clear()
        if hasattr(self, "tree_item_map"):
            self.tree_item_map.clear()
        if hasattr(self, "file_tree"):
            self.file_tree.delete(*self.file_tree.get_children())
        self.reset_ui_counts()
        
        # Reset progress displays
        self.lbl_progress_val.config(text="0% (0.00 GB)")
        self.lbl_speed_val.config(text="-")
        self.lbl_elapsed_val.config(text="00:00")
        self.lbl_eta_val.config(text="-")
        self.progress_bar.config(mode="determinate", value=0)
        self.scan_header_lbl.config(text="Cihaz Seçin ve Taramayı Başlatın")
        self.scan_progress_lbl.config(text="Taramayı başlattığınızda veriler yer kaplamadan burada listelenecektir.")
        
        # Reset gallery progress displays
        if hasattr(self, "gallery_progress_bar"):
            self.gallery_progress_bar.config(value=0)
        if hasattr(self, "gallery_status_lbl"):
            self.gallery_status_lbl.config(text="Hazır.")
            
        # Update buttons
        self.update_button_states_on_session_close()
        
        # Hide top status frame on session close
        if hasattr(self, "top_status_frame"):
            self.top_status_frame.pack_forget()
        
        # Populate and show gallery sessions again
        self.populate_gallery_sessions()
        self.render_folder_gallery()
        
        messagebox.showinfo("Oturum Kapatıldı", "Oturum başarıyla kapatıldı. Yeni bir tarama başlatabilir veya geçmiş oturum yükleyebilirsiniz.")

    def update_button_states_on_session_close(self):
        # Reset dashboard buttons
        self.start_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.stop_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        if hasattr(self, "close_session_btn") and self.close_session_btn:
            self.close_session_btn.pack_forget()
            
        # Reset gallery buttons
        if hasattr(self, "gallery_start_btn") and self.gallery_start_btn:
            self.gallery_start_btn.config(state="normal")
            self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
            self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
            if hasattr(self, "gallery_backup_btn"):
                self.gallery_backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
            self.gallery_stop_btn.config(state="disabled")
            if hasattr(self, "gallery_close_session_btn") and self.gallery_close_session_btn:
                self.gallery_close_session_btn.pack_forget()

    def show_close_session_buttons(self):
        if hasattr(self, "close_session_btn") and self.close_session_btn:
            self.start_btn.pack_forget()
            self.close_session_btn.pack_forget()
            self.start_btn.pack(side=tk.LEFT)
            self.close_session_btn.pack(side=tk.LEFT, padx=(10, 10))
            
        if hasattr(self, "gallery_close_session_btn") and self.gallery_close_session_btn:
            self.gallery_close_session_btn.pack_forget()
            self.gallery_close_session_btn.pack(side=tk.LEFT, padx=(0, 10))

    def check_for_resume_state(self, force_show_dialog=False):
        if getattr(self, "is_scanning", False) and not getattr(self, "scan_paused", False):
            messagebox.showwarning("Uyarı", "Aktif bir tarama işlemi bulunuyor. Oturumu değiştirmek için önce taramayı durdurmalı veya duraklatmalısınız.")
            return
            
        if getattr(self, "current_session_file", None) is not None and self.active_drive:
            self.save_scan_state()

        import os
        import json
        import datetime
        from tkinter import Toplevel, ttk, simpledialog
        import tkinter as tk
        from tkinter import messagebox
        import shutil
        
        if not os.path.exists("yedekler"):
            os.makedirs("yedekler")
            
        if os.path.exists("scan_state.json"):
            try:
                os.rename("scan_state.json", os.path.join("yedekler", "session_eski_yedek.json"))
            except:
                pass

        # Group backups by session
        sessions_map = {}
        
        # Scan folders in yedekler
        for item in os.listdir("yedekler"):
            item_path = os.path.join("yedekler", item)
            if os.path.isdir(item_path):
                backups = []
                for subfile in os.listdir(item_path):
                    if subfile.startswith("session_") and subfile.endswith(".json"):
                        backups.append(os.path.join(item_path, subfile))
                if backups:
                    sessions_map[item] = backups
            elif item.startswith("session_") and item.endswith(".json"):
                if "root" not in sessions_map:
                    sessions_map["root"] = []
                sessions_map["root"].append(item_path)
                
        # If no previous sessions exist, just return on startup
        if not sessions_map:
            return

        # Create split Toplevel dialog
        session_win = Toplevel(self)
        session_win.title("Kurtarma Seansı ve Yedek Seçici")
        session_win.geometry("820x490")
        session_win.configure(bg="#1E1E24")
        session_win.transient(self)
        session_win.grab_set()
        
        title_lbl = tk.Label(session_win, text="Geçmiş Kurtarma Seansları", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 12, "bold"))
        title_lbl.pack(anchor="w", padx=20, pady=(15, 5))
        
        desc_lbl = tk.Label(session_win, text="Soldan bir kurtarma seansı (klasör) seçin ve sağdan yüklemek istediğiniz yedek noktasını belirleyin:", bg="#1E1E24", fg="#A4B0BE", font=("Segoe UI", 9))
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 10))
        
        # Split Frame
        main_split = tk.Frame(session_win, bg="#1E1E24")
        main_split.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        # Left Panel (Sessions list)
        left_frame = tk.Frame(main_split, bg="#1E1E24")
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))
        
        lbl_left = tk.Label(left_frame, text="1. Seanslar (Klasörler)", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"))
        lbl_left.pack(anchor="w", pady=(0, 5))
        
        # Left Panel Management
        left_manage_frame = tk.Frame(left_frame, bg="#1E1E24")
        left_manage_frame.pack(fill=tk.X, pady=(5, 0))
        
        scroll_left_y = ttk.Scrollbar(left_frame, orient="vertical")
        scroll_left_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        style = ttk.Style()
        style.configure("SessionsPicker.Treeview", 
                        background="#FFFFFF", 
                        foreground="#000000", 
                        fieldbackground="#FFFFFF", 
                        font=("Segoe UI", 9))
        
        tree_sessions = ttk.Treeview(left_frame, selectmode="browse", style="SessionsPicker.Treeview", yscrollcommand=scroll_left_y.set)
        tree_sessions.pack(fill=tk.BOTH, expand=True)
        scroll_left_y.config(command=tree_sessions.yview)
        
        tree_sessions["columns"] = ("folder",)
        tree_sessions.column("#0", width=180, anchor="w")
        tree_sessions.column("folder", width=0, stretch=False)
        tree_sessions.heading("#0", text="Seans Adı / Tarih", anchor="w")
        
        # Right Panel (Backups of selected session)
        right_frame = tk.Frame(main_split, bg="#1E1E24")
        right_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        lbl_right = tk.Label(right_frame, text="2. Oturum Yedekleri (JSON Dosyaları)", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"))
        lbl_right.pack(anchor="w", pady=(0, 5))
        
        # Right Panel Management
        right_manage_frame = tk.Frame(right_frame, bg="#1E1E24")
        right_manage_frame.pack(fill=tk.X, pady=(5, 0))
        
        scroll_right_y = ttk.Scrollbar(right_frame, orient="vertical")
        scroll_right_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_backups = ttk.Treeview(right_frame, selectmode="browse", style="SessionsPicker.Treeview", yscrollcommand=scroll_right_y.set)
        tree_backups.pack(fill=tk.BOTH, expand=True)
        scroll_right_y.config(command=tree_backups.yview)
        
        tree_backups["columns"] = ("drive", "progress", "files")
        tree_backups.column("#0", width=140, anchor="w")
        tree_backups.column("drive", width=90, anchor="w")
        tree_backups.column("progress", width=80, anchor="center")
        tree_backups.column("files", width=90, anchor="center")
        
        tree_backups.heading("#0", text="Tarih / Saat", anchor="w")
        tree_backups.heading("drive", text="Sürücü", anchor="w")
        tree_backups.heading("progress", text="İlerleme", anchor="center")
        tree_backups.heading("files", text="Dosyalar", anchor="center")
        
        backup_details = {}
        
        def on_session_select(event):
            tree_backups.delete(*tree_backups.get_children())
            backup_details.clear()
            
            selection = tree_sessions.selection()
            if not selection:
                return
            node = selection[0]
            s_folder = tree_sessions.item(node, "values")[0]
            
            files = sessions_map.get(s_folder, [])
            for b_file in sorted(files, reverse=True):
                try:
                    with open(b_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    timestamp = data.get("timestamp", "")
                    if not timestamp:
                        mtime = os.path.getmtime(b_file)
                        timestamp = datetime.datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M:%S")
                        
                    drive = data.get("active_drive", "Bilinmeyen")
                    if "PhysicalDrive" in drive:
                        drive_num = drive.split("PhysicalDrive")[-1]
                        drive = f"Disk {drive_num}"
                    else:
                        drive = os.path.basename(drive)
                        
                    offset = data.get("resume_offset", 0)
                    size = data.get("active_drive_size", 0)
                    pct = (offset / size * 100) if size > 0 else 0.0
                    progress_str = f"%{pct:.1f}"
                    
                    v_files = data.get("virtual_files", [])
                    files_str = f"{len(v_files)} dosya"
                    
                    fname = os.path.basename(b_file)
                    display_fname = fname
                    if "cikis" in fname:
                        display_fname = f"🚪 Çıkış Kaydı ({timestamp})"
                    elif "auto" in fname:
                        display_fname = f"🔄 Oto Yedek ({timestamp})"
                    else:
                        display_fname = f"💾 Manuel Yedek ({timestamp})"
                        
                    b_node = tree_backups.insert("", "end", text=display_fname, values=(drive, progress_str, files_str))
                    backup_details[b_node] = (b_file, data)
                except Exception as e:
                    print(f"Error loading backup details for {b_file}: {e}")
            
            b_children = tree_backups.get_children()
            if b_children:
                tree_backups.selection_set(b_children[0])
                tree_backups.focus(b_children[0])
                
        tree_sessions.bind("<<TreeviewSelect>>", on_session_select)
        
        # Management Logic
        def refresh_dialog_data():
            sessions_map.clear()
            for item in os.listdir("yedekler"):
                item_path = os.path.join("yedekler", item)
                if os.path.isdir(item_path):
                    backups = []
                    for subfile in os.listdir(item_path):
                        if subfile.startswith("session_") and subfile.endswith(".json"):
                            backups.append(os.path.join(item_path, subfile))
                    if backups:
                        sessions_map[item] = backups
                elif item.startswith("session_") and item.endswith(".json"):
                    if "root" not in sessions_map:
                        sessions_map["root"] = []
                    sessions_map["root"].append(item_path)
            
            sel_sessions = tree_sessions.selection()
            selected_folder = None
            if sel_sessions:
                selected_folder = tree_sessions.item(sel_sessions[0], "values")[0]
                
            tree_sessions.delete(*tree_sessions.get_children())
            tree_backups.delete(*tree_backups.get_children())
            backup_details.clear()
            
            session_folders = sorted(list(sessions_map.keys()), reverse=True)
            for s_folder in session_folders:
                display_name = s_folder
                if s_folder.startswith("oturum_"):
                    parts = s_folder.split("_", 2)
                    if len(parts) >= 3:
                        date_part = parts[1]
                        time_part = parts[2].replace("-", ":")
                        display_name = f"📅 Seans {date_part} {time_part}"
                elif s_folder == "root":
                    display_name = "📂 Ana Dizin Yedekleri"
                
                node = tree_sessions.insert("", "end", text=display_name, values=(s_folder,))
                if s_folder == selected_folder:
                    tree_sessions.selection_set(node)
                    tree_sessions.focus(node)
            
            if not tree_sessions.selection() and tree_sessions.get_children():
                first = tree_sessions.get_children()[0]
                tree_sessions.selection_set(first)
                tree_sessions.focus(first)
                
            on_session_select(None)

        def rename_session():
            selection = tree_sessions.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen yeniden adlandırmak istediğiniz seansı seçin!", parent=session_win)
                return
            node = selection[0]
            s_folder = tree_sessions.item(node, "values")[0]
            
            if s_folder == "root":
                messagebox.showwarning("Uyarı", "Ana dizin yedeklerinin klasör adı değiştirilemez!", parent=session_win)
                return
                
            old_path = os.path.join("yedekler", s_folder)
            if not os.path.exists(old_path):
                return
                
            new_name = simpledialog.askstring("Seans Adını Değiştir", "Yeni seans adını girin (Örn: Tatil_Taramasi):", parent=session_win)
            if not new_name:
                return
                
            new_name = "".join(c for c in new_name if c.isalnum() or c in (" ", "_", "-")).strip()
            if not new_name:
                messagebox.showerror("Hata", "Geçersiz seans adı!", parent=session_win)
                return
                
            new_folder_name = f"oturum_{new_name}"
            new_path = os.path.join("yedekler", new_folder_name)
            
            if os.path.exists(new_path):
                messagebox.showerror("Hata", "Bu isimde bir seans zaten mevcut!", parent=session_win)
                return
                
            try:
                os.rename(old_path, new_path)
                refresh_dialog_data()
            except Exception as e:
                messagebox.showerror("Hata", f"Seans adı değiştirilemedi: {e}", parent=session_win)

        def safe_rmtree(dir_path):
            import stat
            import time
            import gc
            
            gc.collect()
            
            def remove_readonly(func, p, excinfo):
                try:
                    os.chmod(p, stat.S_IWRITE)
                    func(p)
                except:
                    pass
                    
            for i in range(10):
                try:
                    shutil.rmtree(dir_path, onerror=remove_readonly)
                    return True
                except Exception as ex:
                    if i == 9:
                        has_backups = False
                        if os.path.exists(dir_path):
                            try:
                                for root_dir, _, files in os.walk(dir_path):
                                    for file in files:
                                        if file.endswith(".json"):
                                            has_backups = True
                                            break
                            except:
                                pass
                        if has_backups:
                            raise ex
                        return True
                    time.sleep(0.15)
                    gc.collect()
            return False

        def safe_remove(file_path):
            import stat
            import time
            import gc
            
            gc.collect()
            for i in range(10):
                try:
                    if os.path.exists(file_path):
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    return True
                except Exception as ex:
                    if i == 9:
                        if not os.path.exists(file_path):
                            return True
                        raise ex
                    time.sleep(0.15)
                    gc.collect()
            return False

        def delete_session():
            selection = tree_sessions.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz seansı seçin!", parent=session_win)
                return
            node = selection[0]
            s_folder = tree_sessions.item(node, "values")[0]
            
            if s_folder == "root":
                confirm = messagebox.askyesno("Oturum Sil", "Ana dizindeki TÜM yedek dosyalarını kalıcı olarak silmek istediğinizden emin misiniz?", parent=session_win)
                if not confirm:
                    return
                for file_path in sessions_map.get("root", []):
                    try:
                        safe_remove(file_path)
                    except Exception as e:
                        print(f"Error removing loose root backup: {e}")
            else:
                confirm = messagebox.askyesno("Oturum Sil", f"'{s_folder}' seansını ve içindeki TÜM yedekleri kalıcı olarak silmek istediğinizden emin misiniz?", parent=session_win)
                if not confirm:
                    return
                path = os.path.join("yedekler", s_folder)
                try:
                    safe_rmtree(path)
                except Exception as e:
                    messagebox.showerror("Hata", f"Seans silinemedi: {e}", parent=session_win)
                    
            refresh_dialog_data()

        def rename_backup():
            selection = tree_backups.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen yeniden adlandırmak istediğiniz yedeği seçin!", parent=session_win)
                return
            node = selection[0]
            b_file, data = backup_details[node]
            
            new_name = simpledialog.askstring("Yedek Adını Değiştir", "Yeni yedek açıklamasını girin:", parent=session_win)
            if not new_name:
                return
                
            new_name = "".join(c for c in new_name if c.isalnum() or c in (" ", "_", "-")).strip()
            if not new_name:
                messagebox.showerror("Hata", "Geçersiz yedek adı!", parent=session_win)
                return
                
            dir_name = os.path.dirname(b_file)
            prefix = "session_"
            if "cikis" in os.path.basename(b_file):
                prefix = "session_cikis_"
            elif "auto" in os.path.basename(b_file):
                prefix = "session_auto_"
                
            new_file_path = os.path.join(dir_name, f"{prefix}{new_name}.json")
            if os.path.exists(new_file_path):
                messagebox.showerror("Hata", "Bu isimde bir yedek dosyası zaten mevcut!", parent=session_win)
                return
                
            try:
                os.rename(b_file, new_file_path)
                refresh_dialog_data()
            except Exception as e:
                messagebox.showerror("Hata", f"Yedek adı değiştirilemedi: {e}", parent=session_win)

        def delete_backup():
            selection = tree_backups.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen silmek istediğiniz yedeği seçin!", parent=session_win)
                return
            node = selection[0]
            b_file, data = backup_details[node]
            
            confirm = messagebox.askyesno("Yedek Sil", "Bu yedek noktasını kalıcı olarak silmek istediğinizden emin misiniz?", parent=session_win)
            if not confirm:
                return
                
            try:
                safe_remove(b_file)
                dir_name = os.path.dirname(b_file)
                if os.path.basename(dir_name) != "yedekler":
                    if not [f for f in os.listdir(dir_name) if f.endswith(".json")]:
                        try:
                            safe_rmtree(dir_name)
                        except:
                            pass
                refresh_dialog_data()
            except Exception as e:
                messagebox.showerror("Hata", f"Yedek silinemedi: {e}", parent=session_win)

        # Add management buttons to Left Panel
        btn_rename_session = tk.Button(left_manage_frame, text="✏️ Seansı Yeniden Adlandır", command=rename_session, bg="#2F3542", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), borderwidth=0, cursor="hand2", padx=6, pady=4)
        btn_rename_session.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_delete_session = tk.Button(left_manage_frame, text="🗑️ Seansı Sil", command=delete_session, bg="#FF4757", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), borderwidth=0, cursor="hand2", padx=6, pady=4)
        btn_delete_session.pack(side=tk.LEFT)
        
        # Add management buttons to Right Panel
        btn_rename_backup = tk.Button(right_manage_frame, text="✏️ Yedeği Yeniden Adlandır", command=rename_backup, bg="#2F3542", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), borderwidth=0, cursor="hand2", padx=6, pady=4)
        btn_rename_backup.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_delete_backup = tk.Button(right_manage_frame, text="🗑️ Yedeği Sil", command=delete_backup, bg="#FF4757", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), borderwidth=0, cursor="hand2", padx=6, pady=4)
        btn_delete_backup.pack(side=tk.LEFT)

        # Re-populate Sessions List
        session_folders = sorted(list(sessions_map.keys()), reverse=True)
        tree_sessions.delete(*tree_sessions.get_children())
        for s_folder in session_folders:
            display_name = s_folder
            if s_folder.startswith("oturum_"):
                parts = s_folder.split("_", 2)
                if len(parts) >= 3:
                    date_part = parts[1]
                    time_part = parts[2].replace("-", ":")
                    display_name = f"📅 Seans {date_part} {time_part}"
            elif s_folder == "root":
                display_name = "📂 Ana Dizin Yedekleri"
            
            tree_sessions.insert("", "end", text=display_name, values=(s_folder,))
            
        # Buttons
        btn_frame = tk.Frame(session_win, bg="#1E1E24", pady=15)
        btn_frame.pack(fill=tk.X)
        
        selected_session = [None]
        
        def load_session():
            b_selection = tree_backups.selection()
            if not b_selection:
                messagebox.showwarning("Uyarı", "Lütfen sağ taraftan devam etmek istediğiniz bir yedek dosyası seçin veya 'Yeni Oturum Başlat' deyin!")
                return
            node = b_selection[0]
            selected_session[0] = backup_details[node]
            session_win.destroy()
            
        def new_scan():
            selected_session[0] = "new"
            session_win.destroy()
            
        load_btn = tk.Button(btn_frame, text="Seçilen Yedekten Devam Et", command=load_session, bg=self.accent_blue, fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8)
        load_btn.pack(side=tk.LEFT, padx=(20, 10))
        
        new_btn = tk.Button(btn_frame, text="Yeni Oturum Başlat / Sıfırdan Başla", command=new_scan, bg="#2F3542", fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8)
        new_btn.pack(side=tk.LEFT)
        
        s_children = tree_sessions.get_children()
        if s_children:
            tree_sessions.selection_set(s_children[0])
            tree_sessions.focus(s_children[0])
            on_session_select(None)
            
        tree_backups.bind("<Double-1>", lambda event: load_session())
        tree_backups.bind("<Return>", lambda event: load_session())
        
        def on_close():
            selected_session[0] = "new"
            session_win.destroy()
            
        session_win.protocol("WM_DELETE_WINDOW", on_close)
        
        self.wait_window(session_win)
        
        if selected_session[0] == "new" or selected_session[0] is None:
            self.current_session_file = None
        else:
            s_file, data = selected_session[0]
            ok = self.load_selected_session(s_file, data)
            if ok is False:
                self.check_for_resume_state(force_show_dialog=True)

    def show_backup_selector_flow(self):
        import os
        import json
        import datetime
        from tkinter import Toplevel, messagebox, simpledialog
        import tkinter as tk
        import shutil
        
        if getattr(self, "is_scanning", False) and not getattr(self, "scan_paused", False):
            messagebox.showwarning("Uyarı", "Aktif bir tarama işlemi bulunuyor. Yedek değiştirmek için önce taramayı durdurmalı veya duraklatmalısınız.")
            return
            
        if not getattr(self, "current_session_file", None):
            messagebox.showinfo("Bilgi", "Aktif bir kurtarma oturumu bulunmuyor. Yeni bir oturum başlatabilir veya Oturumu Değiştir butonunu kullanabilirsiniz.")
            return
            
        session_dir = os.path.dirname(self.current_session_file)
        if not os.path.exists(session_dir) or not os.path.isdir(session_dir):
            messagebox.showerror("Hata", "Aktif oturumun klasörü bulunamadı.")
            return
            
        backup_files = []
        for file in os.listdir(session_dir):
            if file.startswith("session_") and file.endswith(".json"):
                backup_files.append(os.path.join(session_dir, file))
                
        if not backup_files:
            messagebox.showinfo("Bilgi", "Bu oturum için kaydedilmiş herhangi bir yedek bulunamadı.")
            return
            
        backup_win = Toplevel(self)
        backup_win.title("Oturum Yedeği Değiştirici")
        backup_win.geometry("640x410")
        backup_win.configure(bg="#1E1E24")
        backup_win.transient(self)
        backup_win.grab_set()
        
        title_lbl = tk.Label(backup_win, text=f"Aktif Oturum: {os.path.basename(session_dir)}", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 11, "bold"))
        title_lbl.pack(anchor="w", padx=20, pady=(15, 5))
        
        desc_lbl = tk.Label(backup_win, text="Yüklemek istediğiniz yedek dosyasını seçin:", bg="#1E1E24", fg="#A4B0BE", font=("Segoe UI", 9))
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 10))
        
        list_frame = tk.Frame(backup_win, bg="#1E1E24")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        scroll_y = ttk.Scrollbar(list_frame, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        style = ttk.Style()
        style.configure("BackupPicker.Treeview", 
                        background="#FFFFFF", 
                        foreground="#000000", 
                        fieldbackground="#FFFFFF", 
                        font=("Segoe UI", 9))
        
        tree = ttk.Treeview(list_frame, selectmode="browse", style="BackupPicker.Treeview", yscrollcommand=scroll_y.set)
        tree.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=tree.yview)
        
        tree["columns"] = ("name", "drive", "progress", "files")
        tree.column("#0", width=130, anchor="w")
        tree.column("name", width=140, anchor="w")
        tree.column("drive", width=90, anchor="w")
        tree.column("progress", width=80, anchor="center")
        tree.column("files", width=90, anchor="center")
        
        tree.heading("#0", text="Tarih / Saat", anchor="w")
        tree.heading("name", text="Yedek Dosyası", anchor="w")
        tree.heading("drive", text="Sürücü", anchor="w")
        tree.heading("progress", text="İlerleme", anchor="center")
        tree.heading("files", text="Dosyalar", anchor="center")
        
        manage_frame = tk.Frame(backup_win, bg="#1E1E24")
        manage_frame.pack(fill=tk.X, padx=20, pady=(5, 0))
        
        backup_details = {}
        
        def refresh_curr_backups():
            backup_files.clear()
            for file in os.listdir(session_dir):
                if file.startswith("session_") and file.endswith(".json"):
                    backup_files.append(os.path.join(session_dir, file))
                    
            tree.delete(*tree.get_children())
            backup_details.clear()
            
            for b_file in sorted(backup_files, reverse=True):
                try:
                    with open(b_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    timestamp = data.get("timestamp", "")
                    if not timestamp:
                        mtime = os.path.getmtime(b_file)
                        timestamp = datetime.datetime.fromtimestamp(mtime).strftime("%d.%m.%Y %H:%M:%S")
                        
                    drive = data.get("active_drive", "Bilinmeyen")
                    if "PhysicalDrive" in drive:
                        drive_num = drive.split("PhysicalDrive")[-1]
                        drive = f"Disk {drive_num}"
                    else:
                        drive = os.path.basename(drive)
                        
                    offset = data.get("resume_offset", 0)
                    size = data.get("active_drive_size", 0)
                    pct = (offset / size * 100) if size > 0 else 0.0
                    progress_str = f"%{pct:.1f}"
                    
                    v_files = data.get("virtual_files", [])
                    files_str = f"{len(v_files)} dosya"
                    
                    fname = os.path.basename(b_file)
                    node = tree.insert("", "end", text=timestamp, values=(fname, drive, progress_str, files_str))
                    backup_details[node] = (b_file, data)
                except Exception as e:
                    print(f"Error loading backup metadata: {e}")
                    
            children = tree.get_children()
            if children:
                tree.selection_set(children[0])
                tree.focus(children[0])

        def rename_curr_backup():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen bir yedek seçin!", parent=backup_win)
                return
            node = selection[0]
            b_file, data = backup_details[node]
            
            new_name = simpledialog.askstring("Yedek Adını Değiştir", "Yeni yedek açıklamasını girin:", parent=backup_win)
            if not new_name:
                return
                
            new_name = "".join(c for c in new_name if c.isalnum() or c in (" ", "_", "-")).strip()
            if not new_name:
                messagebox.showerror("Hata", "Geçersiz yedek adı!", parent=backup_win)
                return
                
            prefix = "session_"
            if "cikis" in os.path.basename(b_file):
                prefix = "session_cikis_"
            elif "auto" in os.path.basename(b_file):
                prefix = "session_auto_"
                
            new_file_path = os.path.join(session_dir, f"{prefix}{new_name}.json")
            if os.path.exists(new_file_path):
                messagebox.showerror("Hata", "Bu isimde bir yedek dosyası zaten mevcut!", parent=backup_win)
                return
                
            try:
                os.rename(b_file, new_file_path)
                refresh_curr_backups()
            except Exception as e:
                messagebox.showerror("Hata", f"Yedek adı değiştirilemedi: {e}", parent=backup_win)

        def safe_rmtree(dir_path):
            import stat
            import time
            import gc
            
            gc.collect()
            
            def remove_readonly(func, p, excinfo):
                try:
                    os.chmod(p, stat.S_IWRITE)
                    func(p)
                except:
                    pass
                    
            for i in range(10):
                try:
                    shutil.rmtree(dir_path, onerror=remove_readonly)
                    return True
                except Exception as ex:
                    if i == 9:
                        has_backups = False
                        if os.path.exists(dir_path):
                            try:
                                for root_dir, _, files in os.walk(dir_path):
                                    for file in files:
                                        if file.endswith(".json"):
                                            has_backups = True
                                            break
                            except:
                                pass
                        if has_backups:
                            raise ex
                        return True
                    time.sleep(0.15)
                    gc.collect()
            return False

        def safe_remove(file_path):
            import stat
            import time
            import gc
            
            gc.collect()
            for i in range(10):
                try:
                    if os.path.exists(file_path):
                        os.chmod(file_path, stat.S_IWRITE)
                        os.remove(file_path)
                    return True
                except Exception as ex:
                    if i == 9:
                        if not os.path.exists(file_path):
                            return True
                        raise ex
                    time.sleep(0.15)
                    gc.collect()
            return False

        def delete_curr_backup():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen bir yedek seçin!", parent=backup_win)
                return
            node = selection[0]
            b_file, data = backup_details[node]
            
            confirm = messagebox.askyesno("Yedek Sil", "Bu yedek noktasını kalıcı olarak silmek istediğinizden emin misiniz?", parent=backup_win)
            if not confirm:
                return
                
            try:
                safe_remove(b_file)
                if not [f for f in os.listdir(session_dir) if f.endswith(".json")]:
                    try:
                        safe_rmtree(session_dir)
                    except:
                        pass
                    backup_win.destroy()
                    self.close_current_session()
                else:
                    refresh_curr_backups()
            except Exception as e:
                messagebox.showerror("Hata", f"Yedek silinemedi: {e}", parent=backup_win)

        # Add manage buttons
        btn_rename = tk.Button(manage_frame, text="✏️ Yedeği Yeniden Adlandır", command=rename_curr_backup, bg="#2F3542", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), borderwidth=0, cursor="hand2", padx=6, pady=4)
        btn_rename.pack(side=tk.LEFT, padx=(0, 5))
        
        btn_delete = tk.Button(manage_frame, text="🗑️ Yedeği Sil", command=delete_curr_backup, bg="#FF4757", fg="#FFFFFF", font=("Segoe UI", 8, "bold"), borderwidth=0, cursor="hand2", padx=6, pady=4)
        btn_delete.pack(side=tk.LEFT)

        refresh_curr_backups()
                
        # Buttons
        btn_frame = tk.Frame(backup_win, bg="#1E1E24", pady=15)
        btn_frame.pack(fill=tk.X)
        
        def load_backup():
            selection = tree.selection()
            if not selection:
                messagebox.showwarning("Uyarı", "Lütfen bir yedek seçin!", parent=backup_win)
                return
            node = selection[0]
            b_file, data = backup_details[node]
            backup_win.destroy()
            
            if getattr(self, "current_session_file", None) is not None:
                self.save_scan_state()
                
            self.load_selected_session(b_file, data)
            messagebox.showinfo("Başarılı", f"Yedek başarıyla yüklendi: {os.path.basename(b_file)}", parent=self)
            
        load_btn = tk.Button(btn_frame, text="Seçilen Yedeği Yükle", command=load_backup, bg="#2ECC71", fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8)
        load_btn.pack(side=tk.LEFT, padx=(20, 10))
        
        cancel_btn = tk.Button(btn_frame, text="İptal", command=backup_win.destroy, bg="#57606F", fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8)
        cancel_btn.pack(side=tk.LEFT)
        
        tree.bind("<Double-1>", lambda event: load_backup())
        tree.focus_set()
        self.wait_window(backup_win)

    def setup_new_session_flow(self):
        import os
        import datetime
        from tkinter import filedialog, messagebox
        
        selected_drive = self.active_drive
        if not selected_drive:
            selected_disp = getattr(self, "gallery_drive_var", getattr(self, "drive_var", None))
            if selected_disp:
                selected_drive = self.drives_map.get(selected_disp.get())
                
        # Resolve target directory automatically if not already set or if invalid
        suggested_root = self.get_default_target_drive_root()
        if suggested_root:
            abs_suggested = os.path.abspath(os.path.join(suggested_root, "kurtarilan_dosyalar"))
            if not getattr(self, "selected_output_dir", None) or (selected_drive and self.is_same_disk(selected_drive, self.selected_output_dir)):
                self.selected_output_dir = abs_suggested

        # Check if the currently set output directory is valid
        is_valid = False
        if getattr(self, "selected_output_dir", None):
            abs_dir = os.path.abspath(self.selected_output_dir)
            if not (selected_drive and self.is_same_disk(selected_drive, abs_dir)):
                is_valid = True
                
        if not is_valid:
            # Inform the user to pick a target directory (preferably a separate disk/flash drive)
            messagebox.showinfo(
                "Kurtarma Konumu Belirleyin",
                "Sanal taramaya başlamadan önce lütfen kurtarılan dosyaların kaydedileceği klasörü/diski seçin.\n\n"
                "ÖNEMLİ (VERİ GÜVENLİĞİ): Taradığınız diskin dışında farklı bir fiziksel disk veya takılı bir USB flash bellek seçmelisiniz. Kaynak disk ile hedef disk aynı seçilemez!"
            )
            
            while True:
                target_dir = filedialog.askdirectory(title="Kurtarılan Dosyaların Kaydedileceği Klasörü Seçin")
                if not target_dir:
                    # User cancelled folder picker
                    return False
                    
                abs_dir = os.path.abspath(target_dir)
                if selected_drive and self.is_same_disk(selected_drive, abs_dir):
                    messagebox.showerror(
                        "Kritik Hata: Aynı Disk Seçilemez!", 
                        "Hata: Kurtarma yapmak istediğiniz hedef disk ile kaynak disk aynı fiziksel disk üzerindedir!\n\n"
                        "Verilerin üst üste yazılmasını (overwrite) ve kalıcı veri kaybını önlemek için kurtarma konumunu farklı bir fiziksel diske (örneğin harici bir USB bellek veya farklı bir sürücü) ayarlamalısınız."
                    )
                    continue
                break
                
            self.selected_output_dir = abs_dir
            
        if hasattr(self, "path_lbl") and self.path_lbl:
            self.path_lbl.config(text=self.selected_output_dir)
            
        # Create YYYY-MM-DD_HH-MM-SS timestamp
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        session_dir = os.path.join("yedekler", f"oturum_{timestamp}")
        os.makedirs(session_dir, exist_ok=True)
        self.current_session_file = os.path.join(session_dir, f"session_{timestamp}.json")
        
        # Write initial state
        self.save_scan_state()
        self.show_close_session_buttons()
        return True

    def load_selected_session(self, session_path, state):
        # 1. Disk Connection Verification
        import re, subprocess, os, time
        from tkinter import messagebox
        
        # Resolve source friendly name
        source_name = state.get("kaynak_disk_adi")
        if not source_name:
            source_drive_path = state.get("active_drive") or state.get("kaynak_disk") or ""
            m = re.search(r"PhysicalDrive(\d+)", source_drive_path, re.IGNORECASE)
            if m:
                num = m.group(1)
                try:
                    cmd_src = f'powershell -Command "Get-Disk -Number {num} | Select-Object -ExpandProperty FriendlyName"'
                    res_src = subprocess.run(cmd_src, capture_output=True, text=True, shell=True)
                    source_name = res_src.stdout.strip() if res_src.returncode == 0 else ""
                except:
                    pass
            if not source_name:
                source_name = source_drive_path
                
        # Resolve target friendly name
        target_name = state.get("hedef_disk_adi")
        if not target_name:
            target_dir_path = state.get("selected_output_dir") or state.get("hedef_disk") or ""
            drive_letter = os.path.splitdrive(target_dir_path)[0]
            if drive_letter:
                drive_letter = drive_letter.replace(":", "").strip().upper()
                try:
                    cmd_tgt = f'powershell -Command "Get-Partition -DriveLetter {drive_letter} | Get-Disk | Select-Object -ExpandProperty FriendlyName"'
                    res_tgt = subprocess.run(cmd_tgt, capture_output=True, text=True, shell=True)
                    target_name = res_tgt.stdout.strip() if res_tgt.returncode == 0 else ""
                except:
                    pass
            if not target_name:
                target_name = drive_letter + " Sürücüsü" if drive_letter else target_dir_path

        # Verification loop
        while True:
            current_drives = self.get_current_physical_drives()
            current_partitions = self.get_current_partitions()
            
            # Find matched source drive
            matched_source = None
            if source_name:
                for d in current_drives:
                    if d["name"].lower().strip() == source_name.lower().strip():
                        matched_source = d
                        break
                        
            if not matched_source:
                # Try fallback by number
                m = re.search(r"PhysicalDrive(\d+)", state.get("active_drive", ""), re.IGNORECASE)
                if m:
                    num = int(m.group(1))
                    for d in current_drives:
                        if d["number"] == num:
                            matched_source = d
                            break
                            
            # Find matched target partition
            matched_target_part = None
            if target_name:
                for p in current_partitions:
                    if p["friendly_name"].lower().strip() == target_name.lower().strip():
                        matched_target_part = p
                        break
                        
            if not matched_target_part:
                # Try fallback by letter
                target_dir_path = state.get("selected_output_dir") or state.get("hedef_disk") or ""
                drive_letter = os.path.splitdrive(target_dir_path)[0]
                if drive_letter:
                    drive_letter = drive_letter.replace(":", "").strip().upper()
                    for p in current_partitions:
                        if p["drive_letter"] == drive_letter:
                            matched_target_part = p
                            break
                            
            missing = []
            if not matched_source:
                missing.append(f"Kaynak Disk: {source_name}")
            if not matched_target_part:
                missing.append(f"Hedef Disk: {target_name}")
                
            if missing:
                missing_str = "\n".join(missing)
                res = messagebox.askretrycancel(
                    "Disk Bağlantı Hatası",
                    f"Yedek seansındaki şu disk(ler) şu anda sistemde bulunamadı:\n\n{missing_str}\n\n"
                    "Lütfen disklerin bağlı olduğundan emin olun ve yeniden deneyin."
                )
                if res:
                    self.load_physical_drives()
                    time.sleep(1.0)
                    continue
                else:
                    return False
            else:
                # Update paths in state
                new_source_path = rf"\\.\PhysicalDrive{matched_source['number']}"
                state["active_drive"] = new_source_path
                state["active_drive_size"] = matched_source["size"]
                
                old_target_dir = state.get("selected_output_dir") or state.get("hedef_disk") or ""
                old_drive_letter = os.path.splitdrive(old_target_dir)[0]
                new_drive_letter = matched_target_part["drive_letter"] + ":"
                
                if old_drive_letter and old_drive_letter.upper() != new_drive_letter.upper():
                    new_target_dir = new_drive_letter + old_target_dir[len(old_drive_letter):]
                    state["selected_output_dir"] = new_target_dir
                    print(f"Hedef disk harfi güncellendi: {old_drive_letter} -> {new_drive_letter}")
                    
                break

        self.current_session_file = session_path
        
        self.active_drive = state.get("active_drive")
        self.active_drive_size = state.get("active_drive_size", 0)
        self.resume_offset = state.get("resume_offset", 0)
        self.virtual_files = state.get("virtual_files", [])
        self.elapsed_seconds = state.get("elapsed_seconds", 0.0)
        self.selected_output_dir = state.get("selected_output_dir", os.path.abspath("kurtarilan_dosyalar"))
        if hasattr(self, "path_lbl") and self.path_lbl:
            self.path_lbl.config(text=self.selected_output_dir)
            
        self.scan_source = state.get("scan_source", "dashboard")
        
        self.use_parallel_var.set(state.get("use_parallel", False))
        self.worker_count_var.set(state.get("worker_count", "4"))
        self.segment_size_gb_var.set(state.get("segment_size_gb", "100"))
        self.search_unscanned_var.set(state.get("search_unscanned", False))
        self.scan_from_end_var.set(state.get("scan_from_end", False))
        
        self.use_custom_range_var.set(state.get("use_custom_range", False))
        self.custom_block_range_var.set(state.get("custom_block_range", "1-100"))
        self.custom_start_var.set(state.get("custom_start", "0"))
        self.custom_end_var.set(state.get("custom_end", "100"))
        self.custom_unit_var.set(state.get("custom_unit", "GB"))
        self.scan_start_offset = state.get("scan_start_offset", 0)
        self.scan_end_offset = state.get("scan_end_offset", self.active_drive_size)
        
        raw_progress = state.get("segment_progress", {})
        self.segment_progress = {}
        for k, v in raw_progress.items():
            try:
                self.segment_progress[int(k)] = int(v)
            except (ValueError, TypeError):
                self.segment_progress[k] = v
                
        raw_bounds = state.get("segment_bounds", {})
        self.segment_bounds = {}
        for k, v in raw_bounds.items():
            try:
                self.segment_bounds[int(k)] = int(v)
            except (ValueError, TypeError):
                self.segment_bounds[k] = v
                
        raw_ntfs = state.get("ntfs_deleted_files", {})
        self.ntfs_deleted_files = {}
        if raw_ntfs:
            for k, v in raw_ntfs.items():
                try:
                    self.ntfs_deleted_files[int(k)] = v
                except ValueError:
                    self.ntfs_deleted_files[k] = v
                    
        self.block_copy_counts = state.get("block_copy_counts", [0] * 100)
        self.block_unwanted_counts = state.get("block_unwanted_counts", [0] * 100)
        
        # Sync drive combo box display
        if hasattr(self, "drives_map") and self.drives_map:
            # Find matching display string for drive path
            disp_str = ""
            for k, v in self.drives_map.items():
                if v == self.active_drive:
                    disp_str = k
                    break
            if disp_str:
                self.drive_var.set(disp_str)
                if hasattr(self, "gallery_drive_var"):
                    self.gallery_drive_var.set(disp_str)
                if hasattr(self, "on_drive_select"):
                    self.on_drive_select()
                    
        self.update_ui_counters()
        self.update_file_listbox_view()
        self.draw_disk_map()
        
        # Load in paused state so user can resume
        self.is_scanning = True
        self.scan_paused = True
        
        # Enable control buttons on both Dashboard and Gallery so user can resume from either view
        if hasattr(self, "gallery_start_btn") and self.gallery_start_btn:
            self.gallery_start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
            self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
            self.gallery_resume_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
            if hasattr(self, "gallery_backup_btn"):
                self.gallery_backup_btn.config(state="normal", bg="#FF9F43", fg=self.text_white)
            self.gallery_stop_btn.config(state="normal")
        
        self.start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.resume_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.backup_btn.config(state="normal", bg="#FF9F43", fg=self.text_white)
        self.stop_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        
        offset_gb = self.resume_offset / (1024*1024*1024)
        total_size_gb = self.active_drive_size / (1024*1024*1024)
        
        range_size = (self.scan_end_offset - self.scan_start_offset) if getattr(self, "scan_start_offset", None) is not None else self.active_drive_size
        if range_size <= 0: range_size = self.active_drive_size
        
        total_scanned_bytes = sum(self.segment_progress.values()) if getattr(self, "segment_progress", None) else 0
        
        current_pct = (total_scanned_bytes / range_size * 100) if range_size > 0 else 0.0
        if current_pct > 100: current_pct = 100.0
        
        entire_pct = (total_scanned_bytes / self.active_drive_size * 100) if self.active_drive_size > 0 else 0.0
        if entire_pct > 100: entire_pct = 100.0
        
        self.progress_bar.config(mode="determinate", value=current_pct)
        self.lbl_progress_val.config(text=f"{current_pct:.1f}% ({total_scanned_bytes / (1024*1024*1024):.2f} GB / {range_size / (1024*1024*1024):.2f} GB)")
        
        if hasattr(self, "entire_progress_bar"):
            self.entire_progress_bar.config(mode="determinate", value=entire_pct)
        if hasattr(self, "lbl_entire_progress_val"):
            self.lbl_entire_progress_val.config(text=f"{entire_pct:.2f}% ({total_scanned_bytes / (1024*1024*1024):.2f} GB / {total_size_gb:.2f} GB)")
        if hasattr(self, "lbl_drive_scanned") and self.lbl_drive_scanned:
            self.lbl_drive_scanned.config(text=f"Taranan Alan: {total_scanned_bytes / (1024*1024*1024):.2f} GB (%{entire_pct:.1f})", fg="#0084FF")
            
        self.lbl_speed_val.config(text="-")
        
        el_hours = int(self.elapsed_seconds // 3600)
        el_mins = int((self.elapsed_seconds % 3600) // 60)
        el_secs = int(self.elapsed_seconds % 60)
        elapsed_str = f"{el_hours:02d}:{el_mins:02d}:{el_secs:02d}" if el_hours > 0 else f"{el_mins:02d}:{el_secs:02d}"
        self.lbl_elapsed_val.config(text=elapsed_str)
        self.lbl_eta_val.config(text="Duraklatıldı")
        
        self.scan_header_lbl.config(text=f'"{self.active_drive}" Taraması Kurtarıldı')
        self.scan_progress_lbl.config(text="Tarama duraklatılmış şekilde yüklendi. DEVAM ET butonuna basarak taramayı sürdürebilirsiniz.")
        self.status_lbl.config(text="Tarama duraklatıldı.")
        self.show_close_session_buttons()
        if hasattr(self, "update_target_drive_status"):
            self.update_target_drive_status()
        return True

    def rollback_to_last_backup(self):
        if not getattr(self, "current_session_file", None) or not os.path.exists(self.current_session_file):
            self.virtual_files = []
            self.segment_progress = {}
            if hasattr(self, "segment_bounds"):
                self.segment_bounds.clear()
            self.update_ui_counters()
            self.update_file_listbox_view()
            self.draw_disk_map()
            return
            
        import json
        try:
            with open(self.current_session_file, "r") as f:
                state = json.load(f)
            
            self.active_drive = state.get("active_drive")
            self.active_drive_size = state.get("active_drive_size", 0)
            self.resume_offset = state.get("resume_offset", 0)
            self.virtual_files = state.get("virtual_files", [])
            self.elapsed_seconds = state.get("elapsed_seconds", 0.0)
            self.selected_output_dir = state.get("selected_output_dir", os.path.abspath("kurtarilan_dosyalar"))
            
            raw_progress = state.get("segment_progress", {})
            self.segment_progress = {}
            for k, v in raw_progress.items():
                try:
                    self.segment_progress[int(k)] = int(v)
                except (ValueError, TypeError):
                    self.segment_progress[k] = v
                    
            raw_ntfs = state.get("ntfs_deleted_files", {})
            self.ntfs_deleted_files = {}
            if raw_ntfs:
                for k, v in raw_ntfs.items():
                    try:
                        self.ntfs_deleted_files[int(k)] = v
                    except ValueError:
                        self.ntfs_deleted_files[k] = v
                        
            self.block_copy_counts = state.get("block_copy_counts", [0] * 100)
            self.block_unwanted_counts = state.get("block_unwanted_counts", [0] * 100)
                        
            self.update_ui_counters()
            self.update_file_listbox_view()
            self.draw_disk_map()
        except Exception as e:
            print(f"Rollback hatası: {e}")
