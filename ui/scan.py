import os
import json
import threading
import time
from tkinter import messagebox
from config import FILE_SIGNATURES
from carver import scan_disk_worker

class ScanMixin:
    def start_recovery(self):
        selected_disp = self.drive_var.get()
        if not selected_disp or selected_disp == "Diskler aranıyor...":
            messagebox.showwarning("Uyarı", "Lütfen kurtarma yapmak istediğiniz diski seçin!")
            return
            
        self.active_drive = self.drives_map.get(selected_disp)
        self.active_drive_size = self.drives_sizes_map.get(selected_disp, 0)
        if not self.active_drive:
            messagebox.showerror("Hata", "Sürücü yolu tespit edilemedi.")
            return

        active_sigs = list(FILE_SIGNATURES.values())

        self.is_scanning = True
        self.scan_paused = False
        
        self.start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.pause_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.stop_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        
        self.virtual_files.clear()
        self.tree_item_map.clear()
        self.file_tree.delete(*self.file_tree.get_children())
        self.reset_ui_counts()
        
        # Reset stats UI
        self.resume_offset = 0
        self.elapsed_seconds = 0.0
        self.lbl_progress_val.config(text="0% (0.00 GB)")
        self.lbl_speed_val.config(text="-")
        self.lbl_elapsed_val.config(text="00:00")
        self.lbl_eta_val.config(text="-")
        
        self.progress_bar.config(mode="determinate", value=0)
        
        self.scan_header_lbl.config(text=f'"{selected_disp.split(":")[1].strip()}" taranıyor')
        self.scan_progress_lbl.config(text="Tarama başlatıldı. Lütfen bekleyin...")
        
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
        start_offset = 0
        end_offset = self.active_drive_size
        
        if self.use_custom_range_var.get():
            start_bytes = parse_to_bytes(self.custom_start_var.get(), self.custom_unit_var.get())
            if start_bytes is None or start_bytes < 0:
                start_bytes = 0
            if start_bytes > self.active_drive_size:
                start_bytes = self.active_drive_size
                
            end_bytes = parse_to_bytes(self.custom_end_var.get(), self.custom_unit_var.get())
            if end_bytes is None or end_bytes > self.active_drive_size:
                end_bytes = self.active_drive_size
            if end_bytes <= start_bytes:
                end_bytes = self.active_drive_size
                
            start_offset = start_bytes
            end_offset = end_bytes
                
        self.scan_start_offset = start_offset
        self.scan_end_offset = end_offset
        
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
            offset = start_offset
            while offset < end_offset:
                end = min(offset + segment_size_bytes, end_offset)
                self.scan_segments.append((offset, end))
                self.segment_progress[offset] = 0
                offset = end
        else:
            worker_count = 1
            self.scan_segments = [(start_offset, end_offset)]
            self.segment_progress[start_offset] = 0
            
        self.active_worker_count = worker_count
        
        # Start the worker threads
        for _ in range(worker_count):
            threading.Thread(target=scan_disk_worker, args=(self, self.active_drive, active_sigs), daemon=True).start()

    def pause_recovery(self):
        self.scan_paused = True
        self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.resume_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.status_lbl.config(text="Tarama duraklatıldı.")

    def resume_recovery(self):
        self.scan_paused = False
        self.pause_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.status_lbl.config(text="Tarama devam ediyor...")
        
        # If thread is not running (e.g. reopened app), start it
        with self.disk_lock:
            thread_not_running = (self.active_disk_handle is None)
            
        if thread_not_running:
            active_sigs = list(FILE_SIGNATURES.values())
            
            self.scan_start_offset = getattr(self, "scan_start_offset", 0)
            self.scan_end_offset = getattr(self, "scan_end_offset", self.active_drive_size)
            
            if not getattr(self, "scan_segments", None):
                # Reconstruct segments list from segment_progress keys
                try:
                    segment_size_gb = float(self.segment_size_gb_var.get())
                except:
                    segment_size_gb = 100.0
                segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)
                
                if self.use_parallel_var.get():
                    self.scan_segments = []
                    offset = self.scan_start_offset
                    while offset < self.scan_end_offset:
                        end = min(offset + segment_size_bytes, self.scan_end_offset)
                        prog = self.segment_progress.get(offset, 0)
                        if prog < (end - offset):
                            self.scan_segments.append((offset, end))
                        offset = end
                else:
                    current_prog = self.segment_progress.get(self.scan_start_offset, 0)
                    self.scan_segments = [(self.scan_start_offset + current_prog, self.scan_end_offset)]
                    
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
                threading.Thread(target=scan_disk_worker, args=(self, self.active_drive, active_sigs), daemon=True).start()

    def stop_recovery(self):
        self.is_scanning = False
        self.scan_paused = False
        self.status_lbl.config(text="Durduruluyor...")
        # Delete scan state since user explicitly finished/stopped it
        try:
            if os.path.exists("scan_state.json"):
                os.remove("scan_state.json")
        except:
            pass

    def save_scan_state(self):
        if not self.active_drive or not self.virtual_files:
            return
        state = {
            "active_drive": self.active_drive,
            "active_drive_size": self.active_drive_size,
            "resume_offset": getattr(self, "resume_offset", 0),
            "virtual_files": self.virtual_files,
            "elapsed_seconds": getattr(self, "elapsed_seconds", 0.0),
            "use_parallel": self.use_parallel_var.get(),
            "worker_count": self.worker_count_var.get(),
            "segment_size_gb": self.segment_size_gb_var.get(),
            "segment_progress": getattr(self, "segment_progress", {}),
            "ntfs_deleted_files": getattr(self, "ntfs_deleted_files", {}),
            "use_custom_range": self.use_custom_range_var.get(),
            "custom_start": self.custom_start_var.get(),
            "custom_end": self.custom_end_var.get(),
            "custom_unit": self.custom_unit_var.get(),
            "scan_start_offset": getattr(self, "scan_start_offset", 0),
            "scan_end_offset": getattr(self, "scan_end_offset", self.active_drive_size)
        }
        try:
            with open("scan_state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=4)
        except Exception as e:
            print(f"Durum kaydedilemedi: {e}")

    def check_for_resume_state(self):
        if os.path.exists("scan_state.json"):
            try:
                with open("scan_state.json", "r", encoding="utf-8") as f:
                    state = json.load(f)
                
                drive_path = state.get("active_drive")
                if not drive_path:
                    return
                    
                # Format scan offset for display
                offset_gb = state.get("resume_offset", 0) / (1024*1024*1024)
                
                confirm = messagebox.askyesno(
                    "Tarama Kaldığı Yerden Devam Etsin mi?",
                    f"Önceki tarama kaydı bulundu:\n"
                    f"Sürücü: {drive_path}\n"
                    f"Bulunan Dosya: {len(state.get('virtual_files', []))}\n"
                    f"İlerleme: {offset_gb:.2f} GB\n\n"
                    f"Bu taramaya kaldığı yerden devam etmek istiyor musunuz?"
                )
                if confirm:
                    self.active_drive = drive_path
                    self.active_drive_size = state.get("active_drive_size", 0)
                    self.resume_offset = state.get("resume_offset", 0)
                    self.virtual_files = state.get("virtual_files", [])
                    self.elapsed_seconds = state.get("elapsed_seconds", 0.0)
                    
                    self.use_parallel_var.set(state.get("use_parallel", False))
                    self.worker_count_var.set(state.get("worker_count", "4"))
                    self.segment_size_gb_var.set(state.get("segment_size_gb", "100"))
                    
                    self.use_custom_range_var.set(state.get("use_custom_range", False))
                    self.custom_start_var.set(state.get("custom_start", "0"))
                    self.custom_end_var.set(state.get("custom_end", "100"))
                    self.custom_unit_var.set(state.get("custom_unit", "GB"))
                    self.scan_start_offset = state.get("scan_start_offset", 0)
                    self.scan_end_offset = state.get("scan_end_offset", self.active_drive_size)
                    
                    raw_progress = state.get("segment_progress", {})
                    self.segment_progress = {}
                    for k, v in raw_progress.items():
                        try:
                            self.segment_progress[int(k)] = v
                        except ValueError:
                            self.segment_progress[k] = v
                            
                    raw_ntfs = state.get("ntfs_deleted_files", {})
                    self.ntfs_deleted_files = {}
                    if raw_ntfs:
                        for k, v in raw_ntfs.items():
                            try:
                                self.ntfs_deleted_files[int(k)] = v
                            except ValueError:
                                self.ntfs_deleted_files[k] = v
                    
                    self.update_ui_counters()
                    self.update_file_listbox_view()
                    self.draw_disk_map()
                    
                    self.is_scanning = True
                    self.scan_paused = True
                    
                    self.start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                    self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                    self.resume_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
                    self.stop_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
                    
                    pct = (self.resume_offset / self.active_drive_size * 100) if self.active_drive_size > 0 else 0.0
                    self.progress_bar.config(mode="determinate", value=pct)
                    self.lbl_progress_val.config(text=f"{pct:.1f}% ({offset_gb:.2f} GB / {self.active_drive_size / (1024*1024*1024):.2f} GB)")
                    self.lbl_speed_val.config(text="-")
                    
                    el_hours = int(self.elapsed_seconds // 3600)
                    el_mins = int((self.elapsed_seconds % 3600) // 60)
                    el_secs = int(self.elapsed_seconds % 60)
                    elapsed_str = f"{el_hours:02d}:{el_mins:02d}:{el_secs:02d}" if el_hours > 0 else f"{el_mins:02d}:{el_secs:02d}"
                    self.lbl_elapsed_val.config(text=elapsed_str)
                    self.lbl_eta_val.config(text="Duraklatıldı")
                    
                    self.scan_header_lbl.config(text=f'"{drive_path}" Taraması Kurtarıldı')
                    self.scan_progress_lbl.config(text="Tarama duraklatılmış şekilde yüklendi. DEVAM ET butonuna basarak taramayı sürdürebilirsiniz.")
                    self.status_lbl.config(text="Tarama duraklatıldı.")
                else:
                    try:
                        os.remove("scan_state.json")
                    except:
                        pass
            except Exception as e:
                print(f"Hata resume state yüklerken: {e}")
