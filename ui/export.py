import os
import threading
from tkinter import messagebox
import time

def safe_delete_file(path, retries=10, delay=0.1):
    for _ in range(retries):
        try:
            if os.path.exists(path):
                os.remove(path)
            return True
        except:
            time.sleep(delay)
    return False

class ExportMixin:
    def export_selected(self):
        selected_files = self.get_selected_virtual_files()
        if not selected_files:
            messagebox.showwarning("Uyarı", "Lütfen kaydetmek istediğiniz dosyaları listeden seçin!")
            return
            
        self.save_files_to_disk(selected_files)

    def export_all(self):
        if not self.virtual_files:
            messagebox.showwarning("Uyarı", "Kurtarılacak hiçbir dosya bulunamadı. Lütfen önce tarama yapın.")
            return
            
        self.save_files_to_disk(self.virtual_files)

    def save_files_to_disk(self, files_list):
        if not self.active_drive:
            messagebox.showerror("Hata", "Aktif sürücü bulunamadı.")
            return
            
        if not files_list:
            messagebox.showinfo("Bilgi", "Kaydedilecek/dışa aktarılacak dosya bulunmamaktadır.")
            return
            
        total_size = sum(f["size"] for f in files_list)
        total_size_str = self.format_size(total_size)
        
        # Check disk space on target partition before initiating export
        import shutil
        test_path = self.selected_output_dir
        while test_path and not os.path.exists(test_path):
            parent = os.path.dirname(test_path)
            if parent == test_path:
                break
            test_path = parent
        if not test_path:
            test_path = "."
            
        try:
            usage = shutil.disk_usage(test_path)
            free_space = usage.free
        except Exception:
            free_space = None
            
        if free_space is not None and free_space < total_size:
            free_str = self.format_size(free_space)
            messagebox.showerror(
                "Yetersiz Disk Alanı", 
                f"Hedef diskte yeterli boş alan yok!\n\n"
                f"Gerekli: {total_size_str}\n"
                f"Mevcut Boş Alan: {free_str}"
            )
            return
            
        confirm = messagebox.askyesno(
            "Dışa Aktarma Onayı", 
            f"Toplam {len(files_list)} dosya ({total_size_str}) dışa aktarılacaktır.\n\n"
            f"Hedef konum: {self.selected_output_dir}\n"
            f"Dosyalar kategorilerine göre alt klasörlere ayrılacaktır.\n\n"
            f"Devam etmek istiyor musunuz?"
        )
        if not confirm:
            return
            
        self.export_cancelled = False
        self.configure_buttons_for_export()
        self.status_lbl.config(text="Dosyalar bilgisayara yazılıyor...")
        
        threading.Thread(target=self._save_worker, args=(files_list,), daemon=True).start()

    def configure_buttons_for_export(self):
        # Disable main dashboard/gallery action buttons to prevent concurrent scans or exports
        for btn_name in ["start_btn", "pause_btn", "resume_btn", "export_sel_btn", "export_all_btn", 
                         "move_to_folder_btn", "gallery_start_btn", "gallery_pause_btn", "gallery_resume_btn"]:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn:
                    btn.config(state="disabled")
        
        # Configure stop buttons as cancel export buttons
        if hasattr(self, "stop_btn") and self.stop_btn:
            self.stop_btn.config(state="normal", text="⏹ Aktarımı İptal Et", command=self.cancel_current_export, bg="#FF4757", fg=self.text_white)
        if hasattr(self, "gallery_stop_btn") and self.gallery_stop_btn:
            self.gallery_stop_btn.config(state="normal", text="⏹ Aktarımı İptal Et", command=self.cancel_current_export, bg="#FF4757", fg=self.text_white)

    def cancel_current_export(self):
        self.export_cancelled = True
        self.status_lbl.config(text="Dışa aktarım iptal ediliyor...")
        if hasattr(self, "gallery_status_lbl") and self.gallery_status_lbl:
            self.gallery_status_lbl.config(text="Dışa aktarım iptal ediliyor...")

    def restore_stop_buttons(self):
        # Restore stop buttons to default scan states
        if hasattr(self, "stop_btn") and self.stop_btn:
            self.stop_btn.config(state="disabled", text="TARAMAYI DURDUR", command=self.stop_recovery, bg="#CED6E0", fg=self.text_gray)
        if hasattr(self, "gallery_stop_btn") and self.gallery_stop_btn:
            self.gallery_stop_btn.config(state="disabled", text="TARAMAYI DURDUR", command=self.stop_recovery, bg="#CED6E0", fg=self.text_gray)
            
        # Re-enable starting/exporting buttons
        for btn_name in ["start_btn", "export_sel_btn", "export_all_btn", "move_to_folder_btn", "gallery_start_btn"]:
            if hasattr(self, btn_name):
                btn = getattr(self, btn_name)
                if btn:
                    btn.config(state="normal")
        # Ensure we set start button back to accent blue
        if hasattr(self, "start_btn") and self.start_btn:
            self.start_btn.config(bg=self.accent_blue, fg=self.text_white)

    def get_export_path_mapping(self):
        default_paths = set()
        for f in self.virtual_files:
            if not f.get("custom_path"):
                ext_name = f["ext"].replace(".", "").lower()
                source_group = f.get("source_group", "file")
                path_str = f"{f['category']}/{ext_name}/{source_group}"
                default_paths.add(path_str)
                
        sorted_default_paths = sorted(list(default_paths))
        path_to_klasor_map = {}
        for idx, path_str in enumerate(sorted_default_paths):
            path_to_klasor_map[path_str] = f"klasor{idx + 1}"
        return path_to_klasor_map
 
    def _save_worker(self, files_list):
        import time
        start_time = time.time()
        exported_count = 0
        path_to_klasor_map = self.get_export_path_mapping()
        
        session_folder = "oturum"
        if self.current_session_file:
            parent_dir = os.path.dirname(self.current_session_file)
            parent_name = os.path.basename(parent_dir)
            if parent_name != "yedekler" and parent_name:
                session_folder = parent_name
            else:
                base = os.path.basename(self.current_session_file)
                name_no_ext = os.path.splitext(base)[0]
                session_folder = name_no_ext.replace("session_", "oturum_")
            
        output_root = os.path.join(self.selected_output_dir, session_folder)
        
        try:
            for f in files_list:
                if getattr(self, "export_cancelled", False):
                    break
                if f.get("exported", False):
                    continue
                if f.get("custom_path"):
                    category_dir = os.path.join(output_root, f["custom_path"])
                else:
                    category_dir = os.path.join(output_root, f["category"])
                    
                if not os.path.exists(category_dir):
                    os.makedirs(category_dir)
                    
                ext = f["ext"].lower()
                out_path = os.path.join(category_dir, f["name"])
                if ext == ".zip":
                    zip_folder_name = f["name"].replace(".zip", "")
                    zip_extract_dir = os.path.join(category_dir, zip_folder_name)
                    if os.path.exists(zip_extract_dir):
                        f["exported"] = True
                        exported_count += 1
                        self.msg_queue.put(("status", f"Kaydediliyor: {exported_count}/{len(files_list)}..."))
                        continue
                elif os.path.exists(out_path) and os.path.getsize(out_path) == f["size"]:
                    f["exported"] = True
                    exported_count += 1
                    self.msg_queue.put(("status", f"Kaydediliyor: {exported_count}/{len(files_list)}..."))
                    continue
                    
                if f["size"] > 50 * 1024 * 1024:
                    chunk_size = 8 * 1024 * 1024
                    bytes_written = 0
                    with open(out_path, "wb") as out:
                        while bytes_written < f["size"]:
                            if getattr(self, "export_cancelled", False):
                                break
                            to_read = min(chunk_size, f["size"] - bytes_written)
                            chunk_bytes = self.read_raw_bytes(f["offset"] + bytes_written, to_read)
                            if not chunk_bytes:
                                break
                            out.write(chunk_bytes)
                            bytes_written += len(chunk_bytes)
                else:
                    file_bytes = self.read_raw_bytes(f["offset"], f["size"])
                    if ext in [".jpg", ".jpeg"]:
                        file_bytes = self.repair_jpeg(file_bytes)
                    
                    with open(out_path, "wb") as out:
                        out.write(file_bytes)
                        
                    if ext == ".mp4":
                        try:
                            if b"moov" not in file_bytes:
                                raw_h264 = self.extract_raw_h264(file_bytes)
                                if raw_h264:
                                    raw_name = f["name"].replace(".mp4", "_ham_akis.h264")
                                    raw_path = os.path.join(category_dir, raw_name)
                                    with open(raw_path, "wb") as out_raw:
                                        out_raw.write(raw_h264)
                        except Exception as e:
                            print(f"H264 ayıklama hatası: {e}")
                            
                # Extract zip contents if it is a ZIP archive
                if ext == ".zip":
                    try:
                        import zipfile
                        import shutil
                        zip_folder_name = f["name"].replace(".zip", "")
                        zip_extract_dir = os.path.join(category_dir, zip_folder_name)
                        os.makedirs(zip_extract_dir, exist_ok=True)
                        with zipfile.ZipFile(out_path) as z:
                            z.extractall(zip_extract_dir)
                        safe_delete_file(out_path)
                        # Set out_path to the folder for modification time setting (or skip it)
                        out_path = zip_extract_dir
                    except Exception as ze:
                        print(f"Zip ayıklama hatası: {ze}")
                        # Clean up corrupt files and folders
                        safe_delete_file(out_path)
                        try: shutil.rmtree(zip_extract_dir)
                        except: pass
                    
                # Set original modification time if available
                epoch = f.get("modified_epoch") or f.get("exif_epoch")
                if epoch:
                    try:
                        import time
                        os.utime(out_path, (time.time(), epoch))
                    except:
                        pass
                        
                f["exported"] = True
                exported_count += 1
                
                # Calculate backup progress percentage and ETA
                import time
                pct = (exported_count / len(files_list)) * 100
                elapsed = time.time() - start_time
                if exported_count > 0 and elapsed > 0:
                    files_per_sec = exported_count / elapsed
                    remaining_files = len(files_list) - exported_count
                    eta = remaining_files / files_per_sec
                else:
                    eta = 0
                self.msg_queue.put(("backup_progress", {
                    "pct": pct,
                    "exported": exported_count,
                    "total": len(files_list),
                    "eta": eta
                }))
                
                self.msg_queue.put(("status", f"Kaydediliyor: {exported_count}/{len(files_list)}..."))
                
            self.save_scan_state()
            if getattr(self, "export_cancelled", False):
                self.msg_queue.put(("finished", f"Dışa aktarma iptal edildi! {exported_count} dosya klasörlerine ayrıldı."))
            else:
                self.msg_queue.put(("finished", f"Dışa aktarma bitti! {exported_count} dosya klasörlerine ayrıldı."))
        except Exception as e:
            self.msg_queue.put(("error", f"Kaydetme sırasında bir hata oluştu: {e}"))
            self.msg_queue.put(("finished", "Dışa aktarma yarıda kesildi."))
        finally:
            self.after(0, self.restore_stop_buttons)

    def repair_jpeg(self, raw_bytes):
        if not raw_bytes.startswith(b"\xff\xd8\xff"):
            return raw_bytes
        # Remove trailing null bytes or padding often left by sector alignment
        cleaned_bytes = raw_bytes.rstrip(b"\x00")
        # Check if it ends with the JPEG EOI (End of Image) marker
        if not cleaned_bytes.endswith(b"\xff\xd9"):
            cleaned_bytes += b"\xff\xd9"
        return cleaned_bytes

    def extract_raw_h264(self, mp4_bytes):
        # Find the mdat box containing the raw video frames
        mdat_idx = mp4_bytes.find(b"mdat")
        if mdat_idx == -1:
            return None
        
        # Start scanning after "mdat"
        start_offset = mdat_idx + 4
        raw_stream = bytearray()
        
        idx = start_offset
        limit = len(mp4_bytes)
        while idx + 4 < limit:
            length = int.from_bytes(mp4_bytes[idx:idx+4], "big")
            idx += 4
            if length <= 0 or idx + length > limit:
                break
            # Append Annex B start code and frame payload
            raw_stream.extend(b"\x00\x00\x00\x01")
            raw_stream.extend(mp4_bytes[idx : idx + length])
            idx += length
            
        return bytes(raw_stream) if len(raw_stream) > 0 else None

    def auto_export_unexported(self):
        # Filter files that have not been exported yet
        unexported_files = [f for f in self.virtual_files if not f.get("exported", False)]
        if not unexported_files:
            return
            
        # Spawn a background thread to export them automatically
        if hasattr(self, "status_lbl") and self.status_lbl:
            self.status_lbl.config(text="Bulunan yeni dosyalar otomatik yedekleniyor...")
        threading.Thread(target=self._auto_save_worker, args=(unexported_files,), daemon=True).start()
 
    def _auto_save_worker(self, files_list):
        import time
        start_time = time.time()
        exported_count = 0
        path_to_klasor_map = self.get_export_path_mapping()
        
        session_folder = "oturum"
        if self.current_session_file:
            parent_dir = os.path.dirname(self.current_session_file)
            parent_name = os.path.basename(parent_dir)
            if parent_name != "yedekler" and parent_name:
                session_folder = parent_name
            else:
                base = os.path.basename(self.current_session_file)
                name_no_ext = os.path.splitext(base)[0]
                session_folder = name_no_ext.replace("session_", "oturum_")
            
        output_root = os.path.join(self.selected_output_dir, session_folder)
        
        try:
            for f in files_list:
                if getattr(self, "export_cancelled", False):
                    break
                if f.get("exported", False):
                    continue
                if f.get("custom_path"):
                    category_dir = os.path.join(output_root, f["custom_path"])
                else:
                    category_dir = os.path.join(output_root, f["category"])
                    
                if not os.path.exists(category_dir):
                    os.makedirs(category_dir)
                    
                ext = f["ext"].lower()
                out_path = os.path.join(category_dir, f["name"])
                if ext == ".zip":
                    zip_folder_name = f["name"].replace(".zip", "")
                    zip_extract_dir = os.path.join(category_dir, zip_folder_name)
                    if os.path.exists(zip_extract_dir):
                        f["exported"] = True
                        exported_count += 1
                        self.msg_queue.put(("status", f"Yedekleniyor: {exported_count}/{len(files_list)}..."))
                        continue
                elif os.path.exists(out_path) and os.path.getsize(out_path) == f["size"]:
                    f["exported"] = True
                    exported_count += 1
                    self.msg_queue.put(("status", f"Yedekleniyor: {exported_count}/{len(files_list)}..."))
                    continue
                    
                if f["size"] > 50 * 1024 * 1024:
                    chunk_size = 8 * 1024 * 1024
                    bytes_written = 0
                    with open(out_path, "wb") as out:
                        while bytes_written < f["size"]:
                            if getattr(self, "export_cancelled", False):
                                break
                            to_read = min(chunk_size, f["size"] - bytes_written)
                            chunk_bytes = self.read_raw_bytes(f["offset"] + bytes_written, to_read)
                            if not chunk_bytes:
                                break
                            out.write(chunk_bytes)
                            bytes_written += len(chunk_bytes)
                else:
                    file_bytes = self.read_raw_bytes(f["offset"], f["size"])
                    if ext in [".jpg", ".jpeg"]:
                        file_bytes = self.repair_jpeg(file_bytes)
                        
                    with open(out_path, "wb") as out:
                        out.write(file_bytes)
                        
                    if ext == ".mp4":
                        try:
                            if b"moov" not in file_bytes:
                                raw_h264 = self.extract_raw_h264(file_bytes)
                                if raw_h264:
                                    raw_name = f["name"].replace(".mp4", "_ham_akis.h264")
                                    raw_path = os.path.join(category_dir, raw_name)
                                    with open(raw_path, "wb") as out_raw:
                                        out_raw.write(raw_h264)
                        except Exception as e:
                            print(f"H264 ayıklama hatası: {e}")
                        
                # Extract zip contents if it is a ZIP archive
                if ext == ".zip":
                    try:
                        import zipfile
                        import shutil
                        zip_folder_name = f["name"].replace(".zip", "")
                        zip_extract_dir = os.path.join(category_dir, zip_folder_name)
                        os.makedirs(zip_extract_dir, exist_ok=True)
                        with zipfile.ZipFile(out_path) as z:
                            z.extractall(zip_extract_dir)
                        safe_delete_file(out_path)
                        out_path = zip_extract_dir
                    except Exception as ze:
                        print(f"Zip ayıklama hatası: {ze}")
                        safe_delete_file(out_path)
                        try: shutil.rmtree(zip_extract_dir)
                        except: pass
                        
                # Set original modification time if available
                epoch = f.get("modified_epoch") or f.get("exif_epoch")
                if epoch:
                    try:
                        import time
                        os.utime(out_path, (time.time(), epoch))
                    except:
                        pass
                        
                f["exported"] = True
                exported_count += 1
                
                # Calculate backup progress percentage and ETA
                import time
                pct = (exported_count / len(files_list)) * 100
                elapsed = time.time() - start_time
                if exported_count > 0 and elapsed > 0:
                    files_per_sec = exported_count / elapsed
                    remaining_files = len(files_list) - exported_count
                    eta = remaining_files / files_per_sec
                else:
                    eta = 0
                self.msg_queue.put(("backup_progress", {
                    "pct": pct,
                    "exported": exported_count,
                    "total": len(files_list),
                    "eta": eta
                }))
                
                self.msg_queue.put(("status", f"Yedekleniyor: {exported_count}/{len(files_list)}..."))
                
            self.save_scan_state()
            if getattr(self, "export_cancelled", False):
                self.msg_queue.put(("status", "Otomatik yedekleme iptal edildi."))
            else:
                self.msg_queue.put(("status", f"Yedekleme tamamlandı! {exported_count} yeni dosya hedef diske yazıldı."))
        except Exception as e:
            print(f"Yedekleme hatası: {e}")
