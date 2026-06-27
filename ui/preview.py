import os
import sys
import io
import time
import threading
import tkinter as tk
from tkinter import messagebox

# Import Pillow if available
try:
    from PIL import Image, ImageTk, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

try:
    import pygame.mixer
except ImportError:
    pass

class PreviewMixin:
    def get_file_exported_path(self, file_meta):
        session_folder = "oturum"
        if getattr(self, "current_session_file", None):
            parent_dir = os.path.dirname(self.current_session_file)
            parent_name = os.path.basename(parent_dir)
            if parent_name != "yedekler" and parent_name:
                session_folder = parent_name
            else:
                base = os.path.basename(self.current_session_file)
                name_no_ext = os.path.splitext(base)[0]
                session_folder = name_no_ext.replace("session_", "oturum_")
                
        output_root = os.path.join(self.selected_output_dir, session_folder)
        
        # Check custom path or category
        if file_meta.get("custom_path"):
            path = os.path.join(output_root, file_meta["custom_path"], file_meta["name"])
        else:
            path = os.path.join(output_root, file_meta["category"], file_meta["name"])
            
        ext = file_meta["ext"].lower()
        if ext == ".zip":
            folder_name = file_meta["name"].replace(".zip", "")
            folder_path = os.path.join(output_root, file_meta["category"], folder_name)
            if os.path.exists(folder_path):
                return folder_path
                
        if os.path.exists(path):
            return path
            
        return None

    def is_file_previewable(self, f):
        if f["ext"].lower() not in [".jpg", ".jpeg", ".png", ".bmp", ".gif"]:
            return False
            
        strictness = getattr(self, "preview_strictness_var", None)
        strictness_val = strictness.get() if strictness else "Normal"
        
        min_size = getattr(self, "min_preview_size_var", None)
        try:
            min_size_bytes = int(min_size.get()) if min_size else 512
        except:
            min_size_bytes = 512
            
        if f["size"] < min_size_bytes:
            f["is_previewable"] = False
            return False
            
        if "is_previewable" in f and "Sıkı" not in strictness_val:
            return f["is_previewable"]
            
        previewable = False
        try:
            if "Sıkı" in strictness_val:
                preview_read_size = min(f["size"], 1024 * 1024)
            else:
                preview_read_size = min(f["size"], 32 * 1024)
                
            if preview_read_size >= 100:
                raw_bytes = self.read_raw_bytes(f["offset"], preview_read_size)
                
                if "Hızlı" not in strictness_val:
                    if (raw_bytes.count(b"\x00") >= len(raw_bytes) * 0.90 or 
                        (len(raw_bytes) > 0 and raw_bytes == raw_bytes[0:1] * len(raw_bytes))):
                        f["is_previewable"] = False
                        return False
                
                if HAS_PILLOW:
                    from PIL import Image as PILImage
                    img = PILImage.open(io.BytesIO(raw_bytes))
                    
                    if img.width <= 0 or img.height <= 0:
                        f["is_previewable"] = False
                        return False
                        
                    if "Sıkı" in strictness_val:
                        img.load()
                        
                    previewable = True
        except:
            pass
            
        f["is_previewable"] = previewable
        return previewable

    def get_preview_status(self, f):
        strictness = getattr(self, "preview_strictness_var", None)
        strictness_val = strictness.get() if strictness else "Normal"
        
        min_size = getattr(self, "min_preview_size_var", None)
        try:
            min_size_bytes = int(min_size.get()) if min_size else 512
        except:
            min_size_bytes = 512
            
        if f["size"] < min_size_bytes:
            return "Önizlenemedi"
            
        if f["ext"].lower() == ".mp4":
            try:
                raw_bytes = self.read_raw_bytes(f["offset"], min(f["size"], 1024))
                if "Hızlı" not in strictness_val:
                    if (raw_bytes.count(b"\x00") >= len(raw_bytes) * 0.90 or 
                        (len(raw_bytes) > 0 and raw_bytes == raw_bytes[0:1] * len(raw_bytes))):
                        return "Önizlenemedi"
                if b"ftyp" in raw_bytes:
                    return "Önizlenebildi"
            except:
                pass
            return "Önizlenemedi"
        elif f["ext"].lower() in [".jpg", ".jpeg", ".png", ".bmp", ".gif"]:
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
            self.vid_status_lbl.config(text="Önizleme hazırlanıyor...")
            self.preview_title.config(text=f"ÖNİZLEME: {file_meta['name'].upper()}")
            self.start_video_preview()
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
            # 1. Try to read from local exported/backup file if it exists (very fast, thread-safe, no sharing violations)
            local_path = self.get_file_exported_path(file_meta)
            raw_bytes = None
            if local_path and os.path.isfile(local_path):
                try:
                    with open(local_path, "rb") as lf:
                        raw_bytes = lf.read(preview_read_size)
                except Exception as le:
                    print(f"Error reading local preview file: {le}")
                    
            # 2. Fall back to raw disk read if local file is missing or failed to read
            if raw_bytes is None:
                raw_bytes = self.read_raw_bytes(file_meta["offset"], preview_read_size)
                
            if ext in [".jpg", ".jpeg"] and hasattr(self, "repair_jpeg"):
                raw_bytes = self.repair_jpeg(raw_bytes)
            
            if ext in [".jpg", ".jpeg", ".png", ".bmp", ".gif"] and HAS_PILLOW:
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

    def toggle_video_play_pause(self):
        if not getattr(self, "active_video_playing", False):
            return
            
        self.video_is_paused = not getattr(self, "video_is_paused", False)
        
        # Determine active components
        is_gallery = (self.active_video_screen == getattr(self, "gallery_vid_screen", None))
        play_btn = self.gallery_vid_play_pause_btn if is_gallery else self.vid_play_pause_btn
        status_lbl = self.gallery_vid_status_lbl if is_gallery else self.vid_status_lbl
        
        if self.video_is_paused:
            play_btn.config(text="▶")
            status_lbl.config(text="Duraklatıldı.")
            if getattr(self, "has_audio", False):
                try: pygame.mixer.music.pause()
                except: pass
            self.video_elapsed_paused = time.time() - self.video_start_time
            if hasattr(self, "vid_center_play_btn") and self.vid_center_play_btn and self.vid_center_play_btn.winfo_exists():
                self.vid_center_play_btn.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        else:
            play_btn.config(text="⏸")
            status_lbl.config(text="Oynatılıyor...")
            if getattr(self, "has_audio", False):
                try: pygame.mixer.music.unpause()
                except: pass
            self.video_start_time = time.time() - getattr(self, "video_elapsed_paused", 0)
            if hasattr(self, "vid_center_play_btn") and self.vid_center_play_btn and self.vid_center_play_btn.winfo_exists():
                self.vid_center_play_btn.place_forget()
            self._update_embedded_video_frame()

    def toggle_video_mute(self):
        self.video_is_muted = not getattr(self, "video_is_muted", False)
        is_gallery = (self.active_video_screen == getattr(self, "gallery_vid_screen", None))
        mute_btn = self.gallery_vid_mute_btn if is_gallery else self.vid_mute_btn
        vol_scale = self.gallery_vid_volume_scale if is_gallery else self.vid_volume_scale
        
        if self.video_is_muted:
            mute_btn.config(text="🔇")
            if pygame.mixer.get_init():
                try: pygame.mixer.music.set_volume(0.0)
                except: pass
        else:
            mute_btn.config(text="🔊")
            vol = float(vol_scale.get()) / 100.0
            if pygame.mixer.get_init():
                try: pygame.mixer.music.set_volume(vol)
                except: pass

    def set_video_volume(self, val):
        if getattr(self, "video_is_muted", False):
            return
        vol = float(val) / 100.0
        self.current_volume = vol
        if pygame.mixer.get_init():
            try: pygame.mixer.music.set_volume(vol)
            except: pass

    def on_timeline_press(self, event):
        self.video_is_scrubbing = True
        if getattr(self, "has_audio", False):
            try: pygame.mixer.music.pause()
            except: pass

    def on_timeline_drag(self, event):
        if not getattr(self, "active_cap", None):
            return
        val = float(self.active_timeline.get())
        self.active_time_lbl.config(text=f"{self.format_time(val)} / {self.format_time(self.video_duration)}")
        
        # Seek frame instantly for real-time scrub preview
        import cv2
        target_frame = int(val * self.video_fps)
        self.active_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        ret, frame = self.active_cap.read()
        if ret:
            self._render_single_frame(frame)

    def on_timeline_release(self, event):
        val = float(self.active_timeline.get())
        self.video_is_scrubbing = False
        
        if getattr(self, "has_audio", False):
            try:
                pygame.mixer.music.play(start=val)
                if getattr(self, "video_is_paused", False):
                    pygame.mixer.music.pause()
            except:
                pass
        else:
            self.video_start_time = time.time() - val
            
        if not getattr(self, "video_is_paused", False):
            self._update_embedded_video_frame()

    def format_time(self, seconds):
        if seconds is None or seconds < 0:
            return "00:00"
        m = int(seconds // 60)
        s = int(seconds % 60)
        return f"{m:02d}:{s:02d}"

    def start_video_preview(self):
        if not self.current_video_meta:
            return
            
        self.vid_status_lbl.config(text="Diskten çıkartılıyor... Lütfen bekleyin.")
        # Setup clean default states
        self.vid_play_pause_btn.config(state="disabled")
        
        threading.Thread(target=self._async_extract_and_play_video, args=(self.current_video_meta,), daemon=True).start()

    def _async_extract_and_play_video(self, file_meta):
        temp_path = os.path.abspath("temp_video_preview.mp4")
        temp_audio_path = os.path.abspath("temp_video_preview.wav")
        import time as pytime
        try:
            # Clean up old previews
            for p in [temp_path, temp_audio_path]:
                if os.path.exists(p):
                    try: os.remove(p)
                    except: pass
            
            # Read first 20MB of video bytes for quick preview
            preview_size = min(file_meta["size"], 20 * 1024 * 1024)
            video_bytes = self.read_raw_bytes(file_meta["offset"], preview_size)
            with open(temp_path, "wb") as f:
                f.write(video_bytes)
                
            self.msg_queue.put(("video_status", "Ses ayıklanıyor..."))
            
            # Extract audio in background thread
            audio_extracted = False
            try:
                import importlib
                moviepy_editor = importlib.import_module("moviepy.editor")
                clip = moviepy_editor.VideoFileClip(temp_path)
                if clip.audio is not None:
                    clip.audio.write_audiofile(temp_audio_path, codec="pcm_s16le", fps=44100, logger=None, verbose=False)
                    audio_extracted = True
                clip.close()
            except Exception as ae:
                print(f"Ses ayıklama hatası: {ae}")
                
            self.msg_queue.put(("video_status", "Video yükleniyor..."))
            
            self.after(0, lambda: self.start_embedded_video_playback(
                temp_path, temp_audio_path, audio_extracted, self.vid_screen, self.vid_status_lbl,
                self.vid_timeline, self.vid_time_lbl, self.vid_play_pause_btn, self.vid_mute_btn, self.vid_volume_scale
            ))
        except Exception as e:
            self.msg_queue.put(("video_error", f"Video yüklenemedi: {e}"))

    def stop_video_preview(self):
        self.stop_embedded_video_playback()
        for p in ["temp_video_preview.mp4", "temp_video_preview.wav"]:
            temp_path = os.path.abspath(p)
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

    def start_embedded_video_playback(self, temp_path, temp_audio_path, audio_extracted, screen_widget, status_widget,
                                      timeline_widget, time_lbl, play_pause_btn, mute_btn, volume_scale):
        self.stop_embedded_video_playback()
        
        import cv2
        import time as pytime
        
        self.active_cap = cv2.VideoCapture(temp_path)
        if not self.active_cap.isOpened():
            status_widget.config(text="Hata: Video dosyası çözümlenemedi.")
            return False
            
        self.active_video_playing = True
        self.active_video_screen = screen_widget
        self.active_video_status = status_widget
        self.active_timeline = timeline_widget
        self.active_time_lbl = time_lbl
        self.active_play_pause_btn = play_pause_btn
        self.active_mute_btn = mute_btn
        self.active_volume_scale = volume_scale
        
        # Read video metrics
        self.video_fps = self.active_cap.get(cv2.CAP_PROP_FPS)
        if self.video_fps <= 0:
            self.video_fps = 25.0
        self.video_total_frames = int(self.active_cap.get(cv2.CAP_PROP_FRAME_COUNT))
        self.video_duration = self.video_total_frames / self.video_fps
        
        # Configure Seek Slider
        self.active_timeline.config(from_=0, to=self.video_duration)
        self.active_timeline.set(0)
        self.active_timeline.bind("<ButtonPress-1>", self.on_timeline_press)
        self.active_timeline.bind("<B1-Motion>", self.on_timeline_drag)
        self.active_timeline.bind("<ButtonRelease-1>", self.on_timeline_release)
        
        # Configure Volume Scale Command
        if not hasattr(self, "current_volume"):
            self.current_volume = 0.7
        self.active_volume_scale.set(int(self.current_volume * 100))
        self.active_volume_scale.config(command=self.set_video_volume)
        
        # Bind Screen Click Play/Pause
        screen_widget.bind("<Button-1>", lambda e: self.toggle_video_play_pause())
        
        # Setup Pygame Mixer Audio
        self.has_audio = False
        if audio_extracted and os.path.exists(temp_audio_path):
            try:
                if not pygame.mixer.get_init():
                    pygame.mixer.init()
                pygame.mixer.music.load(temp_audio_path)
                pygame.mixer.music.set_volume(0.0 if getattr(self, "video_is_muted", False) else self.current_volume)
                pygame.mixer.music.play()
                self.has_audio = True
            except Exception as pe:
                print(f"Pygame ses çalma hatası: {pe}")
                
        self.video_is_paused = True
        self.video_is_scrubbing = False
        self.video_start_time = pytime.time()
        self.video_elapsed_paused = 0
        
        if self.has_audio:
            try: pygame.mixer.music.pause()
            except: pass
            
        play_pause_btn.config(text="▶", state="normal")
        status_widget.config(text="Hazır (Oynatmak için tıklayın).")
        
        # Fetch and render first frame (thumbnail)
        ret, frame = self.active_cap.read()
        if ret:
            self._render_single_frame(frame)
            self.active_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            
        # Set timeline and duration labels
        self.active_timeline.set(0)
        self.active_time_lbl.config(text=f"00:00 / {self.format_time(self.video_duration)}")
        
        # Overlay a play button in the center of the screen
        if not hasattr(self, "vid_center_play_btn") or not self.vid_center_play_btn or not self.vid_center_play_btn.winfo_exists():
            self.vid_center_play_btn = tk.Button(
                screen_widget.master, text="▶", command=self.toggle_video_play_pause,
                bg=self.accent_blue, fg=self.text_white, font=("Segoe UI", 18, "bold"),
                borderwidth=0, relief="flat", activebackground=self.accent_blue,
                activeforeground=self.text_white, width=3, height=1, cursor="hand2"
            )
        self.vid_center_play_btn.place(relx=0.5, rely=0.5, anchor=tk.CENTER)
        
        return True

    def _update_embedded_video_frame(self):
        if not getattr(self, "active_video_playing", False) or not getattr(self, "active_cap", None):
            return
        if getattr(self, "video_is_paused", False) or getattr(self, "video_is_scrubbing", False):
            return
            
        import cv2
        import time as pytime
        
        # Time alignment
        if getattr(self, "has_audio", False):
            pos_ms = pygame.mixer.music.get_pos()
            if pos_ms < 0:
                # Audio finished, loop video
                pygame.mixer.music.play()
                self.video_start_time = pytime.time()
                current_time = 0.0
            else:
                current_time = pos_ms / 1000.0
        else:
            current_time = pytime.time() - self.video_start_time
            if current_time >= self.video_duration:
                # Loop video
                self.video_start_time = pytime.time()
                current_time = 0.0
                
        target_frame = int(current_time * self.video_fps)
        self.active_cap.set(cv2.CAP_PROP_POS_FRAMES, target_frame)
        
        ret, frame = self.active_cap.read()
        if ret:
            self._render_single_frame(frame)
            
            # Update seek bar and time display
            self.active_timeline.set(current_time)
            self.active_time_lbl.config(text=f"{self.format_time(current_time)} / {self.format_time(self.video_duration)}")
            
            # Schedule next frame
            delay = int(1000 / self.video_fps)
            self.active_video_timer = self.after(delay, self._update_embedded_video_frame)
        else:
            # Loop fallback
            if getattr(self, "has_audio", False):
                pygame.mixer.music.play()
            self.video_start_time = pytime.time()
            self.active_cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            self.active_video_timer = self.after(33, self._update_embedded_video_frame)

    def _render_single_frame(self, frame):
        import cv2
        from PIL import Image, ImageTk
        
        canvas_w = self.active_video_screen.winfo_width()
        canvas_h = self.active_video_screen.winfo_height()
        if canvas_w < 10: canvas_w = 320
        if canvas_h < 10: canvas_h = 350
        
        screen_w = canvas_w
        screen_h = canvas_h
        
        h, w = frame.shape[:2]
        aspect = w / h
        if w > screen_w or h > screen_h:
            if aspect > (screen_w / screen_h):
                new_w = screen_w
                new_h = int(screen_w / aspect)
            else:
                new_h = screen_h
                new_w = int(screen_h * aspect)
        else:
            new_w = w
            new_h = h
            
        frame = cv2.resize(frame, (new_w, new_h))
        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        img = Image.fromarray(frame_rgb)
        self.tk_embedded_video_frame = ImageTk.PhotoImage(img)
        
        if self.active_video_screen.winfo_exists():
            self.active_video_screen.delete("all")
            self.active_video_screen.create_image(canvas_w / 2, canvas_h / 2, anchor=tk.CENTER, image=self.tk_embedded_video_frame)

    def stop_embedded_video_playback(self):
        self.active_video_playing = False
        self.video_is_paused = False
        
        if hasattr(self, "vid_center_play_btn") and self.vid_center_play_btn and self.vid_center_play_btn.winfo_exists():
            try: self.vid_center_play_btn.destroy()
            except: pass
            self.vid_center_play_btn = None
            
        if pygame.mixer.get_init():
            try: pygame.mixer.music.stop()
            except: pass
            
        if hasattr(self, "active_video_timer") and self.active_video_timer:
            try: self.after_cancel(self.active_video_timer)
            except: pass
            self.active_video_timer = None
            
        if hasattr(self, "active_cap") and self.active_cap:
            try: self.active_cap.release()
            except: pass
            self.active_cap = None
            
        if hasattr(self, "active_video_screen") and self.active_video_screen and self.active_video_screen.winfo_exists():
            self.active_video_screen.config(image="", text="📺 Video Hazır", fg=self.accent_blue, font=("Segoe UI", 16, "bold"))
            self.active_video_screen.unbind("<Button-1>")
            
        if hasattr(self, "active_timeline") and self.active_timeline and self.active_timeline.winfo_exists():
            self.active_timeline.set(0)
            self.active_timeline.unbind("<ButtonPress-1>")
            self.active_timeline.unbind("<B1-Motion>")
            self.active_timeline.unbind("<ButtonRelease-1>")
            
        if hasattr(self, "active_time_lbl") and self.active_time_lbl and self.active_time_lbl.winfo_exists():
            self.active_time_lbl.config(text="00:00 / 00:00")
            
        if hasattr(self, "active_play_pause_btn") and self.active_play_pause_btn and self.active_play_pause_btn.winfo_exists():
            self.active_play_pause_btn.config(text="▶")
            
        if hasattr(self, "active_video_status") and self.active_video_status and self.active_video_status.winfo_exists():
            self.active_video_status.config(text="Oynatma durduruldu.")
