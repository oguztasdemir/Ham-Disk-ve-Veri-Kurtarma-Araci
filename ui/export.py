import os
import threading
from tkinter import messagebox

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
            
        total_size = sum(f["size"] for f in files_list)
        total_size_str = self.format_size(total_size)
        
        confirm = messagebox.askyesno(
            "Dışa Aktarma Onayı", 
            f"Toplam {len(files_list)} dosya ({total_size_str}) dışa aktarılacaktır.\n\n"
            f"Hedef konum: {self.selected_output_dir}\n"
            f"Dosyalar kategorilerine göre alt klasörlere ayrılacaktır.\n\n"
            f"Devam etmek istiyor musunuz?"
        )
        if not confirm:
            return
            
        self.start_btn.config(state="disabled")
        self.pause_btn.config(state="disabled")
        self.resume_btn.config(state="disabled")
        self.stop_btn.config(state="disabled")
        self.export_sel_btn.config(state="disabled")
        self.export_all_btn.config(state="disabled")
        if hasattr(self, "move_to_folder_btn") and self.move_to_folder_btn:
            self.move_to_folder_btn.config(state="disabled")
        self.status_lbl.config(text="Dosyalar bilgisayara yazılıyor...")
        
        threading.Thread(target=self._save_worker, args=(files_list,), daemon=True).start()
 
    def _save_worker(self, files_list):
        exported_count = 0
        try:
            for f in files_list:
                if f.get("custom_path"):
                    category_dir = os.path.join(self.selected_output_dir, f["custom_path"])
                else:
                    # Group subfolders by file size ranges
                    size_bytes = f["size"]
                    if size_bytes < 100 * 1024:
                        size_group = "Küçük (100KB altı)"
                    elif size_bytes < 1024 * 1024:
                        size_group = "Orta (100KB - 1MB)"
                    elif size_bytes < 10 * 1024 * 1024:
                        size_group = "Büyük (1MB - 10MB)"
                    else:
                        size_group = "Çok Büyük (10MB üstü)"
                    
                    category_dir = os.path.join(self.selected_output_dir, f["category"], size_group)
                    
                if not os.path.exists(category_dir):
                    os.makedirs(category_dir)
                    
                file_bytes = self.read_raw_bytes(f["offset"], f["size"])
                
                # Apply automatic repair filters
                ext = f["ext"].lower()
                if ext in [".jpg", ".jpeg"]:
                    file_bytes = self.repair_jpeg(file_bytes)
                
                out_path = os.path.join(category_dir, f["name"])
                with open(out_path, "wb") as out:
                    out.write(file_bytes)
                    
                # For MP4, if it is corrupt (missing moov), extract the raw H.264 stream
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
                    
                exported_count += 1
                self.msg_queue.put(("status", f"Kaydediliyor: {exported_count}/{len(files_list)}..."))
                
            self.msg_queue.put(("finished", f"Dışa aktarma bitti! {exported_count} dosya klasörlerine ayrıldı."))
        except Exception as e:
            self.msg_queue.put(("error", f"Kaydetme sırasında bir hata oluştu: {e}"))
            self.msg_queue.put(("finished", "Dışa aktarma yarıda kesildi."))

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
