import os
import sys
import io
import threading
import tkinter as tk
from tkinter import messagebox

# Import Pillow if available
try:
    from PIL import Image, ImageTk
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

class PreviewMixin:
    def is_file_previewable(self, f):
        if f["ext"].lower() not in [".jpg", ".jpeg", ".png"]:
            return False
        if "is_previewable" in f:
            return f["is_previewable"]
        previewable = False
        try:
            preview_read_size = min(f["size"], 32 * 1024)
            if preview_read_size >= 100:
                raw_bytes = self.read_raw_bytes(f["offset"], preview_read_size)
                if HAS_PILLOW:
                    from PIL import Image as PILImage
                    PILImage.open(io.BytesIO(raw_bytes))
                    previewable = True
        except:
            pass
        f["is_previewable"] = previewable
        return previewable

    def get_preview_status(self, f):
        if f["ext"].lower() == ".mp4":
            return "Önizlenebildi"
        elif f["ext"].lower() in [".jpg", ".jpeg", ".png"]:
            return "Önizlenebildi" if self.is_file_previewable(f) else "Önizlenemedi"
        return "Önizlenemedi"

    def on_file_select(self, event):
        selection = self.file_tree.selection()
        if not selection:
            return
            
        node_id = selection[0]
        # Only preview if they select a file node
        if node_id not in self.tree_item_map:
            self.preview_canvas.delete("all")
            self.preview_title.config(text="BELLEK ÖNİZLEME")
            self.preview_canvas.create_text(20, 30, anchor="nw", fill=self.text_dark, text="Önizlemek için listeden bir dosya seçin.", font=("Segoe UI", 10, "italic"))
            return
            
        file_meta = self.tree_item_map[node_id]
        self.current_preview_file_id = file_meta["id"]
        
        # Stop any active video preview cleanups
        self.stop_video_preview()
        
        if file_meta["ext"].lower() == ".mp4":
            self.preview_canvas.pack_forget()
            self.preview_video_frame.pack(fill=tk.BOTH, expand=True)
            self.current_video_meta = file_meta
            
            size_str = self.format_size(file_meta["size"])
            self.vid_info_lbl.config(text=f"Dosya: {file_meta['name']}\nBoyut: {size_str}\nOfset: {file_meta['offset']}")
            self.vid_status_lbl.config(text="Oynatmaya hazır.")
            self.preview_title.config(text=f"ÖNİZLEME: {file_meta['name'].upper()}")
            return
        else:
            self.preview_video_frame.pack_forget()
            self.preview_canvas.pack(fill=tk.BOTH, expand=True)
            self.current_video_meta = None
            
            # Display Loading status on canvas
            self.preview_canvas.delete("all")
            self.preview_title.config(text=f"ÖNİZLEME: {file_meta['name'].upper()}")
            self.preview_canvas.create_text(20, 30, anchor="nw", fill=self.text_dark, text="Bellekten yükleniyor...", font=("Segoe UI", 10, "italic"))
            
            # Fetch target sizes safely from main GUI thread geometry
            canvas_w = self.preview_canvas.winfo_width()
            canvas_h = self.preview_canvas.winfo_height()
            if canvas_w < 10: canvas_w = 320
            if canvas_h < 10: canvas_h = 350
            
            # Spawn background preview loader thread to prevent UI freezing
            threading.Thread(target=self._async_load_preview, args=(file_meta, canvas_w, canvas_h), daemon=True).start()

    def _async_load_preview(self, file_meta, canvas_w, canvas_h):
        file_id = file_meta["id"]
        ext = file_meta["ext"].lower()
        
        # Limit preview read size to at most 5MB to prevent memory bloat & lags
        preview_read_size = min(file_meta["size"], 5 * 1024 * 1024)
        
        try:
            raw_bytes = self.read_raw_bytes(file_meta["offset"], preview_read_size)
            
            if ext in [".jpg", ".jpeg", ".png"] and HAS_PILLOW:
                img_data = io.BytesIO(raw_bytes)
                from PIL import Image as PILImage
                img = PILImage.open(img_data)
                
                img.thumbnail((canvas_w - 20, canvas_h - 20))
                img.load() # Force decode here to catch broken stream/corrupt image errors on background thread
                
                self.msg_queue.put(("display_preview", {
                    "file_id": file_id,
                    "type": "image",
                    "pil_image": img,
                    "name": file_meta["name"]
                }))
            else:
                size_mb = file_meta["size"] / (1024 * 1024)
                meta_text = (
                    f"Dosya Adı: {file_meta['name']}\n"
                    f"Kategori: {file_meta['category']}\n"
                    f"Disk Ofseti: {file_meta['offset']} bayt\n"
                    f"Boyut: {size_mb:.2f} MB\n\n"
                    f"[Önizleme Desteklenmiyor]\n"
                    f"Seçilenleri kaydetmek için aşağıdaki butonları kullanın."
                )
                self.msg_queue.put(("display_preview", {
                    "file_id": file_id,
                    "type": "meta",
                    "text": meta_text,
                    "name": file_meta["name"]
                }))
        except Exception as e:
            err_msg = str(e)
            if "cannot identify image file" in err_msg:
                err_msg = "Görsel dosyası bozuk, eksik veya geçersiz (resim formatı çözümlenemedi)."
            self.msg_queue.put(("display_preview", {
                "file_id": file_id,
                "type": "error",
                "text": f"Disk üzerinden önizleme yüklenemedi:\n{err_msg}",
                "name": file_meta["name"]
            }))

    def start_video_preview(self):
        if not self.current_video_meta:
            return
            
        self.vid_status_lbl.config(text="Diskten çıkartılıyor... Lütfen bekleyin.")
        self.vid_play_btn.config(state="disabled")
        
        # Spawn extraction to background thread to avoid freezing UI
        threading.Thread(target=self._async_extract_and_play_video, args=(self.current_video_meta,), daemon=True).start()

    def _async_extract_and_play_video(self, file_meta):
        temp_path = os.path.abspath("temp_video_preview.mp4")
        try:
            # Clean up old preview if exists
            if os.path.exists(temp_path):
                try:
                    os.remove(temp_path)
                except:
                    pass
            
            # Read full video bytes from raw disk sectors
            video_bytes = self.read_raw_bytes(file_meta["offset"], file_meta["size"])
            with open(temp_path, "wb") as f:
                f.write(video_bytes)
                
            self.msg_queue.put(("video_status", "Video sistem oynatıcısında açıldı."))
            
            if sys.platform == "win32":
                os.startfile(temp_path)
            else:
                import subprocess
                if sys.platform == "darwin":
                    subprocess.Popen(["open", temp_path])
                else:
                    subprocess.Popen(["xdg-open", temp_path])
        except Exception as e:
            self.msg_queue.put(("video_error", f"Video oynatılamadı: {e}"))

    def stop_video_preview(self):
        temp_path = os.path.abspath("temp_video_preview.mp4")
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except:
                pass
        self.vid_status_lbl.config(text="Oynatma durduruldu.")
        self.vid_play_btn.config(state="normal")
