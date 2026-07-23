import os
import sys
import threading
import queue
import io
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Import Pillow if available
try:
    from PIL import Image, ImageTk, ImageFile
    ImageFile.LOAD_TRUNCATED_IMAGES = True
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

from config import BG_DARK, SIDEBAR_BG, CONTENT_BG, TEXT_DARK, TEXT_GRAY, ACCENT_BLUE, TEXT_WHITE, CATEGORIES, FILE_SIGNATURES, APP_NAME, APP_VERSION
from carver import read_raw_bytes_shared

from ui.drives import DrivesMixin
from ui.scan import ScanMixin
from ui.preview import PreviewMixin
from ui.export import ExportMixin
from ui.tree import TreeMixin
from ui.layout import LayoutMixin
from ui.gallery import GalleryMixin

class ConsoleRedirector:
    def __init__(self, app):
        self.app = app
        self.stdout = sys.stdout

    def write(self, string):
        if not string:
            return
        self.stdout.write(string)
        try:
            self.app.msg_queue.put(("console_log", string))
        except:
            pass

    def flush(self):
        try:
            self.stdout.flush()
        except:
            pass

class RecoveryApp(tk.Tk, DrivesMixin, ScanMixin, PreviewMixin, ExportMixin, TreeMixin, LayoutMixin, GalleryMixin):
    def __init__(self):
        super().__init__()
        
        self.msg_queue = queue.Queue()
        self.has_logged_error = False
        self.active_log_widget = None
        
        # Redirect stdout and stderr
        self.redirector = ConsoleRedirector(self)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

        self.title(f"{APP_NAME} v{APP_VERSION} - Profesyonel Veri Kurtarma Paneli")
        self.geometry("1320x800")
        self.configure(bg=BG_DARK)
        
        # Color & style assets
        self.bg_dark = BG_DARK
        self.sidebar_bg = SIDEBAR_BG
        self.content_bg = CONTENT_BG
        self.text_dark = TEXT_DARK
        self.text_gray = TEXT_GRAY
        self.accent_blue = ACCENT_BLUE
        self.text_white = TEXT_WHITE
        
        # Thread safety variables
        self.disk_lock = threading.Lock()
        self.segment_lock = threading.Lock()
        self.segment_progress = {}
        self.active_disk_handle = None
        self.active_drive = None
        
        # State variables
        self.is_scanning = False
        self.scan_paused = False
        self.scan_source = "dashboard"
        import time
        self.scan_delay = 0.0  # Controls speed slider (0 = max speed, higher = more sleep)
        self.gui_heartbeat = time.time()
        self.drives_map = {}
        self.drives_sizes_map = {}
        self.active_drive_size = 0
        self.resume_offset = 0
        self.elapsed_seconds = 0.0
        self.msg_queue = queue.Queue()
        self.selected_output_dir = os.path.abspath("kurtarilan_dosyalar")
        self.current_session_file = None
        self.last_auto_export_time = 0.0
        # Migrate old 'sessions' folder to 'yedekler' if it exists and 'yedekler' does not exist
        if os.path.exists("sessions") and not os.path.exists("yedekler"):
            try:
                os.rename("sessions", "yedekler")
            except:
                pass
        if not os.path.exists("yedekler"):
            os.makedirs("yedekler")
        
        # Virtual File Storage
        self.virtual_files = [] 
        self.total_recovered_count = 0
        self.total_recovered_size = 0
        self.category_counts = {c: 0 for c in CATEGORIES.keys()}
        self.category_sizes = {c: 0 for c in CATEGORIES.keys()}
        self.selected_category_filter = "All"
        self.hide_non_previewable = tk.BooleanVar(value=False)
        self.sort_var = tk.StringVar(value="Varsayılan (Bulunma Sırası)")
        self.sort_column = None
        self.sort_descending = False
        self.current_preview_file_id = None
        self.current_gallery_preview_file_id = None
        self.tree_item_map = {}
        self.folder_nodes = {}
        self.folder_stats = {}
        self.tree_reconstructed_node = None
        self.block_copy_counts = [0] * 100
        self.block_unwanted_counts = [0] * 100

        # Parallel and range scan variables
        self.use_parallel_var = tk.BooleanVar(value=False)
        self.worker_count_var = tk.StringVar(value="4")
        self.segment_size_gb_var = tk.StringVar(value="100")
        self.use_custom_range_var = tk.BooleanVar(value=False)
        self.custom_start_var = tk.StringVar(value="0")
        self.custom_end_var = tk.StringVar(value="100")
        self.custom_unit_var = tk.StringVar(value="GB")
        self.custom_block_range_var = tk.StringVar(value="1-100")
        self.search_unscanned_var = tk.BooleanVar(value=False)
        self.scan_from_end_var = tk.BooleanVar(value=False)
        self.tree_needs_update = False
        self.counters_need_update = False
        self.selected_canvas_blocks = set()
        self.last_clicked_block = None

        self.load_app_settings()

        self.create_widgets()
        self.init_folder_gallery_view()
        self.load_physical_drives()
        self.check_queue()
        self.after(100, self.check_for_resume_state)
        self.update_system_stats()
        self.after(1500, self.periodic_tree_refresh)
        self.after(500, self.periodic_ui_refresh)

        # Handle window closing to save state if scanning
        self.protocol("WM_DELETE_WINDOW", self.close_app)

    def load_app_settings(self):
        import json
        self.category_vars = {}
        self.scan_queue = []
        # Default all to True
        for cat in CATEGORIES.keys():
            self.category_vars[cat] = tk.BooleanVar(value=True)
            
        settings_path = "app_settings.json"
        if os.path.exists(settings_path):
            try:
                with open(settings_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    cats = data.get("selected_categories", {})
                    for cat, val in cats.items():
                        if cat in self.category_vars:
                            self.category_vars[cat].set(val)
                    self.scan_queue = data.get("scan_queue", [])
            except Exception as e:
                print(f"Error loading app settings: {e}")
                
    def save_app_settings(self):
        import json
        settings_path = "app_settings.json"
        try:
            cats = {cat: var.get() for cat, var in self.category_vars.items()}
            data = {
                "selected_categories": cats,
                "scan_queue": self.scan_queue
            }
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Error saving app settings: {e}")

    def read_raw_bytes(self, offset, size):
        return read_raw_bytes_shared(self.active_disk_handle or self.active_drive, offset, size, self.disk_lock)

    def format_size(self, size_bytes):
        if size_bytes < 1024:
            return f"{size_bytes} B"
        elif size_bytes < 1024 * 1024:
            return f"{size_bytes / 1024:.2f} KB"
        elif size_bytes < 1024 * 1024 * 1024:
            return f"{size_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

    def calculate_scan_score(self):
        total_files = len(self.virtual_files)
        if total_files == 0:
            return 0, "Bulunan Dosya Yok"
            
        high_chance_count = 0
        medium_chance_count = 0
        for f in self.virtual_files:
            size = f.get("size", 0)
            if size > 1024 * 1024:
                high_chance_count += 1.5
            elif size > 50 * 1024:
                high_chance_count += 1
            else:
                medium_chance_count += 1
                
        raw_score = int((high_chance_count * 10 + medium_chance_count * 5) / max(1, total_files) * 10)
        bonus = min(20, total_files // 5)
        score = min(100, raw_score + bonus)
        if score < 30:
            score = 30
            
        if score >= 85:
            rating = "Mükemmel (Sağlıklı Kurtarma)"
        elif score >= 70:
            rating = "Çok İyi"
        elif score >= 50:
            rating = "İyi"
        else:
            rating = "Orta (Düşük İhtimal)"
            
        return score, rating

    def close_app(self):
        if getattr(self, "active_drive", None):
            self.save_scan_state(force_synchronous=True, is_exit=True)
        self.is_scanning = False
        self.scan_paused = False
        self.destroy()
        try:
            if os.path.exists("app.pid"):
                os.remove("app.pid")
        except:
            pass
        sys.exit(0)

    def check_queue(self):
        processed = 0
        while not self.msg_queue.empty() and processed < 1000:
            processed += 1
            msg_type, data = self.msg_queue.get()
            if msg_type == "loaded_drives":
                self.drive_combo.config(values=data)
                
                # Check if we have an active session drive already loaded
                matching_idx = None
                if getattr(self, "active_drive", None) and hasattr(self, "drives_map") and self.drives_map:
                    for idx, opt in enumerate(data):
                        if self.drives_map.get(opt) == self.active_drive:
                            matching_idx = idx
                            break
                            
                seagate_idx = 0
                for idx, opt in enumerate(data):
                    if "seagate" in opt.lower():
                        seagate_idx = idx
                        break
                
                if data:
                    if matching_idx is not None:
                        self.drive_combo.current(matching_idx)
                    else:
                        # Only set default seagate if we don't have an active session
                        if not getattr(self, "current_session_file", None):
                            self.drive_combo.current(seagate_idx)
                    self.on_drive_select()
                    
                if hasattr(self, "gallery_drive_combo") and self.gallery_drive_combo:
                    self.gallery_drive_combo.config(values=data)
                    if data:
                        if matching_idx is not None:
                            self.gallery_drive_combo.current(matching_idx)
                        else:
                            if not getattr(self, "current_session_file", None):
                                self.gallery_drive_combo.current(seagate_idx)
                        
                        selected_disp = self.gallery_drive_var.get()
                        if selected_disp and hasattr(self, "drives_map"):
                            # Update active_drive only if not in loaded session, or if it matches
                            if not getattr(self, "current_session_file", None) or self.drives_map.get(selected_disp) == self.active_drive:
                                self.active_drive = self.drives_map.get(selected_disp)
                                self.active_drive_size = self.drives_sizes_map.get(selected_disp, 0)
            elif msg_type == "backup_progress":
                pct = data.get("pct", 0.0)
                exported = data.get("exported", 0)
                total = data.get("total", 0)
                eta = data.get("eta", 0)
                
                eta_str = f"{int(eta)} sn" if eta > 0 else "Hesaplanıyor..."
                if exported >= total:
                    status_text = f"Yedekleme Tamamlandı: %100 ({exported}/{total} dosya)"
                    if hasattr(self, "backup_progress_bar"):
                        self.backup_progress_bar.config(value=100)
                else:
                    status_text = f"Yedekleniyor / Aktarılıyor: %{pct:.1f} ({exported}/{total} dosya) | Kalan Yaklaşık Süre: {eta_str}"
                    if hasattr(self, "backup_progress_bar"):
                        self.backup_progress_bar.config(value=pct)
                    
                if hasattr(self, "lbl_backup_progress_val"):
                    self.lbl_backup_progress_val.config(text=status_text)
            elif msg_type == "status":
                self.scan_progress_lbl.config(text=data)
                self.status_lbl.config(text=data)
                if getattr(self, "scan_source", "dashboard") == "gallery":
                    self.gallery_status_lbl.config(text=data)
            elif msg_type == "error":
                # Safely abort scanning state and restore UI buttons
                self.is_scanning = False
                self.scan_paused = False
                
                self.start_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
                self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.stop_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                
                if hasattr(self, "gallery_start_btn"):
                    self.gallery_start_btn.config(state="normal")
                    self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                    self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                    self.gallery_stop_btn.config(state="disabled")
                    
                # Discard unsaved changes and roll back to the last backup file on disk
                self.rollback_to_last_backup()
                
                self.scan_progress_lbl.config(text=f"Tarama durduruldu (Hata: {data})")
                self.status_lbl.config(text=f"Hata: {data}")
                
                err_msg = f"Disk bağlantısı kesildi veya okuma hatası oluştu!\n\nDetaylar: {data}\n\nTarama durduruldu ve durum son başarılı yedeğe geri yüklendi."
                messagebox.showerror("Bağlantı Hatası", err_msg)
            elif msg_type == "progress_update":
                # Update progress bar and metrics
                pct = data.get("pct", 0)
                gb = data.get("gb", 0)
                total_gb = data.get("total_gb", 0)
                speed = data.get("speed", 0)
                elapsed = data.get("elapsed", "00:00")
                eta = data.get("eta", "-")
                
                self.resume_offset = data.get("offset", 0)
                self.elapsed_seconds = data.get("elapsed_seconds", 0.0)
                self.progress_bar.config(mode="determinate", value=pct)
                self.lbl_progress_val.config(text=f"{pct:.1f}% ({gb:.2f} GB / {total_gb:.2f} GB)")
                
                entire_pct = data.get("entire_pct", 0.0)
                entire_gb = data.get("entire_scanned_gb", 0.0)
                entire_total = data.get("entire_total_gb", 0.0)
                if hasattr(self, "entire_progress_bar"):
                    self.entire_progress_bar.config(mode="determinate", value=entire_pct)
                if hasattr(self, "lbl_entire_progress_val"):
                    self.lbl_entire_progress_val.config(text=f"{entire_pct:.2f}% ({entire_gb:.2f} GB / {entire_total:.2f} GB)")

                self.lbl_speed_val.config(text=f"{speed:.2f} MB/s")
                self.lbl_elapsed_val.config(text=elapsed)
                self.lbl_eta_val.config(text=eta)
                self.draw_disk_map()
                if getattr(self, "detail_map_tree", None) and self.detail_map_tree.winfo_exists():
                    self.populate_detail_map_tree(self.detail_map_tree)
                
                current_block = 1
                if getattr(self, "active_drive_size", 0) > 0:
                    current_block = int((getattr(self, "resume_offset", 0) / self.active_drive_size) * 100) + 1
                    current_block = max(1, min(100, current_block))
                
                status_text = f"Taranıyor: %{pct:.1f} | Hız: {speed:.2f} MB/s | Kalan: {eta} | Aktif Blok: {current_block}/100"
                self.scan_progress_lbl.config(text=status_text)
                self.status_lbl.config(text=status_text)
                
                # Update top status labels (split layout with score)
                if hasattr(self, "top_current_scan_lbl") and self.top_current_scan_lbl:
                    current_txt = f"Mevcut Tarama: %{pct:.1f} ({gb:.2f}/{total_gb:.1f} GB) | {speed:.1f} MB/s | Süre: {elapsed} | Kalan: {eta} | Aktif Blok: {current_block}/100"
                    self.top_current_scan_lbl.config(text=current_txt)
                    
                    entire_pct = data.get("entire_pct", 0.0)
                    entire_gb = data.get("entire_scanned_gb", 0.0)
                    entire_total = data.get("entire_total_gb", 0.0)
                    entire_txt = f"Tüm Klasör: %{entire_pct:.2f} ({entire_gb:.2f}/{entire_total:.1f} GB)"
                    self.top_entire_disk_lbl.config(text=entire_txt)
                    
                    # Calculate and display the score
                    score, rating = self.calculate_scan_score()
                    score_txt = f"Tarama Kurtarma Skoru: %{score} ({rating})"
                    self.top_score_lbl.config(text=score_txt)
                    
                    # Determine active view within content_frame to pack top_status_frame before it
                    active_view = None
                    for view in [self.dashboard_view, self.file_view, getattr(self, "folder_gallery_view", None)]:
                        if view and view.winfo_manager() == "pack":
                            active_view = view
                            break
                    if active_view:
                        self.top_status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(10, 5), before=active_view)
                    else:
                        self.top_status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(10, 5))
                
                if getattr(self, "scan_source", "dashboard") == "gallery":
                    self.gallery_status_lbl.config(text="Taranıyor...")
                    self.gallery_progress_bar.config(value=pct)
                
                # Auto-save scan state and export found files to disk every 30 seconds during active scanning
                import time
                curr_t = time.time()
                if curr_t - getattr(self, "last_save_time", 0.0) >= 30.0:
                    self.last_save_time = curr_t
                    self.save_scan_state()
                    self.auto_export_unexported()
            elif msg_type == "recovered_file_meta":
                if getattr(self, "scan_source", "dashboard") == "gallery":
                    # 1. Enforce ONLY previewable images
                    if not data.get("is_previewable"):
                        continue
                
                if "exported" not in data:
                    data["exported"] = False
                self.virtual_files.append(data)
                self.update_ui_counters_fast(data)
                self.tree_needs_update = True
                self.counters_need_update = True
            elif msg_type == "display_preview":
                # Check if the user hasn't selected another file in the meantime
                if self.current_preview_file_id == data["file_id"]:
                    self.preview_canvas.delete("all")
                    self.preview_title.config(text=f"ÖNİZLEME: {data['name'].upper()}")
                    if data["type"] == "image":
                        self.tk_img = ImageTk.PhotoImage(data["pil_image"])
                        canvas_w = self.preview_canvas.winfo_width()
                        canvas_h = self.preview_canvas.winfo_height()
                        if canvas_w < 10: canvas_w = 320
                        if canvas_h < 10: canvas_h = 350
                        self.preview_canvas.create_image(canvas_w/2, canvas_h/2, anchor=tk.CENTER, image=self.tk_img)
                    else:
                        fill_color = "#FF3333" if data["type"] == "error" else self.text_dark
                        self.preview_canvas.create_text(20, 30, anchor="nw", fill=fill_color, text=data["text"], font=("Segoe UI", 10), width=280)
            elif msg_type == "gallery_thumbnail":
                f_path = data["folder_path"]
                pil_img = data["pil_image"]
                try:
                    photo = ImageTk.PhotoImage(pil_img)
                    self.gallery_photos[f_path] = photo
                    if f_path in self.gallery_labels:
                        self.gallery_labels[f_path].config(image=photo, text="")
                except Exception as e:
                    print(f"Failed to show gallery thumbnail: {e}")
            elif msg_type == "gallery_card_thumbnail":
                key = data["key"]
                pil_img = data["pil_image"]
                try:
                    photo = ImageTk.PhotoImage(pil_img)
                    self.gallery_photos[key] = photo
                    if key in self.gallery_labels:
                        self.gallery_labels[key].config(image=photo, text="", width=0, height=0)
                except Exception as e:
                    print(f"Failed to show card thumbnail: {e}")
            elif msg_type == "gallery_detail_thumbnail":
                file_id = data["file_id"]
                pil_img = data["pil_image"]
                try:
                    photo = ImageTk.PhotoImage(pil_img)
                    self.gallery_photos[f"detail_{file_id}"] = photo
                    if file_id in self.gallery_detail_labels:
                        self.gallery_detail_labels[file_id].config(image=photo, text="")
                except Exception as e:
                    print(f"Failed to show gallery detail thumbnail: {e}")
            elif msg_type == "gallery_display_preview":
                if self.current_gallery_preview_file_id == data["file_id"]:
                    self.gallery_preview_canvas.delete("all")
                    self.gallery_preview_title.config(text=f"ÖNİZLEME: {data['name'].upper()}")
                    if data["type"] == "image":
                        self.tk_gallery_img = ImageTk.PhotoImage(data["pil_image"])
                        canvas_w = self.gallery_preview_canvas.winfo_width()
                        canvas_h = self.gallery_preview_canvas.winfo_height()
                        if canvas_w < 10: canvas_w = 320
                        if canvas_h < 10: canvas_h = 350
                        self.gallery_preview_canvas.create_image(canvas_w/2, canvas_h/2, anchor=tk.CENTER, image=self.tk_gallery_img)
                    else:
                        fill_color = "#FF3333" if data["type"] == "error" else self.text_dark
                        self.gallery_preview_canvas.create_text(20, 30, anchor="nw", fill=fill_color, text=data["text"], font=("Segoe UI", 10), width=280)
            elif msg_type == "gallery_video_status":
                self.gallery_vid_status_lbl.config(text=data)
                self.gallery_vid_play_pause_btn.config(state="normal")
            elif msg_type == "gallery_video_error":
                self.gallery_vid_status_lbl.config(text=data)
                self.gallery_vid_play_pause_btn.config(state="normal")
                messagebox.showerror("Hata", data)
            elif msg_type == "video_status":
                self.vid_status_lbl.config(text=data)
                self.vid_play_pause_btn.config(state="normal")
            elif msg_type == "video_error":
                self.vid_status_lbl.config(text=data)
                self.vid_play_pause_btn.config(state="normal")
                messagebox.showerror("Hata", data)
            elif msg_type == "console_log":
                message = data
                # Append to app log buffer with a cap to prevent infinite memory growth
                self.console_logs.append(message)
                if len(self.console_logs) > 2000:
                    self.console_logs = self.console_logs[-2000:]
                
                # Check if it contains traceback or error
                lower_msg = message.lower()
                if "error" in lower_msg or "exception" in lower_msg or "traceback" in lower_msg or "hata" in lower_msg:
                    self.trigger_error_warning()
                    
                # If the console window is currently open, write to it in real time
                if hasattr(self, "active_log_widget") and self.active_log_widget:
                    try:
                        self.active_log_widget.config(state="normal")
                        self.active_log_widget.insert(tk.END, message)
                        
                        # Limit lines in text widget to 1000 to prevent Tkinter slow-down/freeze
                        num_lines = int(self.active_log_widget.index('end-1c').split('.')[0])
                        if num_lines > 1000:
                            self.active_log_widget.delete("1.0", f"{num_lines - 1000}.0")
                            
                        self.active_log_widget.config(state="disabled")
                        self.active_log_widget.see(tk.END)
                    except:
                        pass

                # If the embedded dashboard log is active, write to it in real time
                if hasattr(self, "dash_log_text") and self.dash_log_text:
                    try:
                        self.dash_log_text.config(state="normal")
                        self.dash_log_text.insert(tk.END, message)
                        
                        # Limit lines in text widget to 1000 to prevent Tkinter slow-down/freeze
                        num_lines = int(self.dash_log_text.index('end-1c').split('.')[0])
                        if num_lines > 1000:
                            self.dash_log_text.delete("1.0", f"{num_lines - 1000}.0")
                            
                        self.dash_log_text.config(state="disabled")
                        self.dash_log_text.see(tk.END)
                    except:
                        pass
            elif msg_type == "finished":
                self.progress_bar.config(mode="determinate", value=100)
                self.start_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
                self.pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.stop_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                if hasattr(self, "export_sel_btn") and self.export_sel_btn:
                    self.export_sel_btn.config(state="normal")
                if hasattr(self, "export_all_btn") and self.export_all_btn:
                    self.export_all_btn.config(state="normal")
                if hasattr(self, "move_to_folder_btn") and self.move_to_folder_btn:
                    self.move_to_folder_btn.config(state="normal")
                
                self.is_scanning = False
                self.scan_paused = False
                
                if getattr(self, "scan_source", "dashboard") == "gallery":
                    self.gallery_progress_bar.config(value=100)
                    self.gallery_start_btn.config(state="normal")
                    self.gallery_stop_btn.config(state="disabled")
                    self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                    self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                    self.gallery_status_lbl.config(text=data)
                    self.render_folder_gallery()
                
                if hasattr(self, "top_current_scan_lbl") and self.top_current_scan_lbl:
                    self.top_current_scan_lbl.config(text="Mevcut Tarama: Tamamlandı!")
                    self.top_entire_disk_lbl.config(text="Tüm Klasör: Tarama Bitti")
                    score, rating = self.calculate_scan_score()
                    self.top_score_lbl.config(text=f"Tarama Kurtarma Skoru: %{score} ({rating})")
                    # Determine active view within content_frame to pack top_status_frame before it
                    active_view = None
                    for view in [self.dashboard_view, self.file_view, getattr(self, "folder_gallery_view", None)]:
                        if view and view.winfo_manager() == "pack":
                            active_view = view
                            break
                    if active_view:
                        self.top_status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(10, 5), before=active_view)
                    else:
                        self.top_status_frame.pack(side=tk.TOP, fill=tk.X, padx=20, pady=(10, 5))
                
                # Update advanced settings inputs state to enable them now that scan is finished
                if hasattr(self, "toggle_parallel_options"):
                    self.toggle_parallel_options()
                if hasattr(self, "toggle_gallery_adv_options"):
                    self.toggle_gallery_adv_options()
                
                # Delete state since scan is finished
                try:
                    if os.path.exists("scan_state.json"):
                        os.remove("scan_state.json")
                except:
                    pass
                
                self.scan_progress_lbl.config(text=data)
                self.status_lbl.config(text=data)
                messagebox.showinfo("Tarama Bitti", data)
            elif msg_type == "save_state_success":
                self.status_lbl.config(text="Yedek alınmıştır.")
                if hasattr(self, "gallery_status_lbl") and self.gallery_status_lbl:
                    self.gallery_status_lbl.config(text="Yedek alınmıştır.")
                if hasattr(self, "backup_progress_bar"):
                    self.backup_progress_bar.config(value=100)
                if hasattr(self, "lbl_backup_progress_val"):
                    self.lbl_backup_progress_val.config(text="Yedekleme/Durum Kaydı başarıyla tamamlandı!")
                
        self.after(100, self.check_queue)

    def update_ui_counters(self):
        self.total_recovered_count = len(self.virtual_files)
        self.total_recovered_size = sum(f["size"] for f in self.virtual_files)
        self.all_files_btn.config(text=f"📁 Tüm Dosyalar ({self.total_recovered_count} - {self.format_size(self.total_recovered_size)})")
        
        self.category_counts = {c: 0 for c in CATEGORIES.keys()}
        self.category_sizes = {c: 0 for c in CATEGORIES.keys()}
        
        for f in self.virtual_files:
            cat = f["category"]
            if cat in self.category_counts:
                self.category_counts[cat] += 1
                self.category_sizes[cat] += f["size"]
            else:
                self.category_counts["Diğer"] += 1
                self.category_sizes["Diğer"] += f["size"]
                
        for cat_name, val in self.category_counts.items():
            icon = CATEGORIES[cat_name]["icon"]
            cat_size = self.category_sizes[cat_name]
            self.sidebar_buttons[cat_name].config(text=f"{icon} {cat_name} ({val} - {self.format_size(cat_size)})")
            self.card_widgets[cat_name]["count_lbl"].config(text=f"{val} Dosya ({self.format_size(cat_size)})")

    def update_ui_counters_fast(self, new_file):
        self.total_recovered_count += 1
        self.total_recovered_size += new_file["size"]
        
        cat = new_file["category"]
        if cat in self.category_counts:
            self.category_counts[cat] += 1
            self.category_sizes[cat] += new_file["size"]
        else:
            self.category_counts["Diğer"] += 1
            self.category_sizes["Diğer"] += new_file["size"]

    def reset_ui_counts(self):
        self.total_recovered_count = 0
        self.total_recovered_size = 0
        self.category_counts = {c: 0 for c in CATEGORIES.keys()}
        self.category_sizes = {c: 0 for c in CATEGORIES.keys()}
        self.block_copy_counts = [0] * 100
        self.block_unwanted_counts = [0] * 100
        
        self.all_files_btn.config(text="📁 Tüm Dosyalar (0)")
        for cat_name in CATEGORIES.keys():
            self.sidebar_buttons[cat_name].config(text=f"{CATEGORIES[cat_name]['icon']} {cat_name} (0)")
            self.card_widgets[cat_name]["count_lbl"].config(text="0 Dosya Bulundu")

    def trigger_error_warning(self):
        self.has_logged_error = True
        if hasattr(self, "log_btn"):
            self.log_btn.config(text="⚠️ Konsol Hatası!", bg="#FF4757", fg=self.text_white)

    def show_console_log_window(self):
        # Create a new top-level log window
        log_win = tk.Toplevel(self)
        log_win.title("Konsol Log Akışı")
        log_win.geometry("700x500")
        log_win.configure(bg="#1E1E24")
        log_win.transient(self)
        
        title_frame = tk.Frame(log_win, bg="#1E1E24")
        title_frame.pack(fill=tk.X, padx=15, pady=10)
        
        title_lbl = tk.Label(title_frame, text="Terminal Çıktısı & Log Akışı", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 12, "bold"))
        title_lbl.pack(side=tk.LEFT)
        
        def copy_to_clipboard():
            self.clipboard_clear()
            self.clipboard_append("".join(self.console_logs))
            messagebox.showinfo("Başarılı", "Konsol logları panoya kopyalandı!")
            
        copy_btn = tk.Button(title_frame, text="📋 Konsolu Kopyala", command=copy_to_clipboard, bg=self.accent_blue, fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=10, pady=4, cursor="hand2")
        copy_btn.pack(side=tk.RIGHT)
        
        txt_frame = tk.Frame(log_win, bg="#1E1E24")
        txt_frame.pack(fill=tk.BOTH, expand=True, padx=15, pady=(0, 15))
        
        scroll_y = ttk.Scrollbar(txt_frame, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        log_text = tk.Text(txt_frame, bg="#2F3542", fg="#FFFFFF", insertbackground="white", yscrollcommand=scroll_y.set, font=("Consolas", 10), state="normal")
        log_text.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=log_text.yview)
        
        # Populate current logs
        log_text.insert(tk.END, "".join(self.console_logs))
        log_text.config(state="disabled")
        log_text.see(tk.END)
        
        self.active_log_widget = log_text
        
        def on_close():
            self.active_log_widget = None
            log_win.destroy()
            
        log_win.protocol("WM_DELETE_WINDOW", on_close)

    def is_same_disk(self, drive_path, target_dir):
        if not drive_path or not target_dir:
            return False
            
        import os
        import re
        import subprocess
        
        # 1. Extract drive letter from target_dir (e.g. D)
        drive_letter = os.path.splitdrive(target_dir)[0]
        if not drive_letter:
            return False
        drive_letter = drive_letter.replace(":", "").strip().upper()
        if not drive_letter.isalpha():
            return False
            
        # 2. Extract DiskNumber from drive_path (e.g. 2 from \\.\PhysicalDrive2)
        m = re.search(r"PhysicalDrive(\d+)", drive_path, re.IGNORECASE)
        if not m:
            m2 = re.search(r"\\\\.\\([A-Za-z]):", drive_path)
            if m2:
                source_letter = m2.group(1).upper()
                return source_letter == drive_letter
            return False
            
        disk_num = m.group(1)
        
        # 3. Query FriendlyName of source and target
        try:
            # Query source friendly name
            cmd_src = f'powershell -Command "Get-Disk -Number {disk_num} | Select-Object -ExpandProperty FriendlyName"'
            res_src = subprocess.run(cmd_src, capture_output=True, text=True, shell=True)
            source_name = res_src.stdout.strip() if res_src.returncode == 0 else ""
            
            # Query target friendly name
            cmd_tgt = f'powershell -Command "Get-Partition -DriveLetter {drive_letter} | Get-Disk | Select-Object -ExpandProperty FriendlyName"'
            res_tgt = subprocess.run(cmd_tgt, capture_output=True, text=True, shell=True)
            target_name = res_tgt.stdout.strip() if res_tgt.returncode == 0 else ""
            
            if source_name and target_name:
                # If friendly names are different, they are different physical disks!
                return source_name.lower().strip() == target_name.lower().strip()
        except Exception as e:
            print(f"Friendly name check error: {e}")
            
        # Fallback to DiskNumber matching
        try:
            cmd = f'powershell -Command "Get-Partition -DriveLetter {drive_letter} | Select-Object -ExpandProperty DiskNumber"'
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if res.returncode == 0 and res.stdout.strip():
                target_disk_num = res.stdout.strip()
                return target_disk_num == disk_num
        except Exception as e:
            print(f"DiskNumber check error: {e}")
            
        return False

    def get_friendly_name_of_drive(self, drive_path):
        if not drive_path:
            return ""
        # 1. Try to find in self.drives_details_map
        if hasattr(self, "drives_map") and hasattr(self, "drives_details_map"):
            for display_str, path in self.drives_map.items():
                if path == drive_path:
                    details = self.drives_details_map.get(display_str)
                    if details and details.get("name"):
                        return details["name"]
        
        # 2. Fallback to querying powershell
        import re, subprocess
        m = re.search(r"PhysicalDrive(\d+)", drive_path, re.IGNORECASE)
        if m:
            num = m.group(1)
            try:
                cmd = f'powershell -Command "Get-Disk -Number {num} | Select-Object -ExpandProperty FriendlyName"'
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if res.returncode == 0 and res.stdout.strip():
                    return res.stdout.strip()
            except:
                pass
        return os.path.basename(drive_path)

    def get_friendly_name_of_target(self, target_dir):
        if not target_dir:
            return ""
        import os, subprocess
        drive_letter = os.path.splitdrive(target_dir)[0]
        if not drive_letter:
            return ""
        drive_letter = drive_letter.replace(":", "").strip().upper()
        if not drive_letter.isalpha():
            return ""
        try:
            cmd = f'powershell -Command "Get-Partition -DriveLetter {drive_letter} | Get-Disk | Select-Object -ExpandProperty FriendlyName"'
            res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if res.returncode == 0 and res.stdout.strip():
                return res.stdout.strip()
        except:
            pass
        return drive_letter + " Sürücüsü"

    def get_current_physical_drives(self):
        import subprocess, json
        drives = []
        try:
            cmd = 'powershell -Command "Get-Disk | Select-Object Number, FriendlyName, Size | ConvertTo-Json"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                for disk in data:
                    drives.append({
                        "number": disk.get("Number"),
                        "name": disk.get("FriendlyName", ""),
                        "size": disk.get("Size", 0)
                    })
        except Exception as e:
            print(f"Error listing physical drives: {e}")
        return drives

    def get_current_partitions(self):
        import subprocess, json
        partitions = []
        try:
            cmd = 'powershell -Command "Get-Partition | Select-Object DiskNumber, DriveLetter | ConvertTo-Json"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                parts_data = json.loads(result.stdout.strip())
                if isinstance(parts_data, dict):
                    parts_data = [parts_data]
                    
                cmd_disks = 'powershell -Command "Get-Disk | Select-Object Number, FriendlyName | ConvertTo-Json"'
                result_disks = subprocess.run(cmd_disks, capture_output=True, text=True, shell=True)
                disks_map = {}
                if result_disks.returncode == 0 and result_disks.stdout.strip():
                    disks_data = json.loads(result_disks.stdout.strip())
                    if isinstance(disks_data, dict):
                        disks_data = [disks_data]
                    for disk in disks_data:
                        disks_map[disk.get("Number")] = disk.get("FriendlyName", "")
                
                for part in parts_data:
                    letter = part.get("DriveLetter")
                    if letter and letter.strip():
                        disk_num = part.get("DiskNumber")
                        friendly_name = disks_map.get(disk_num, "")
                        partitions.append({
                            "disk_number": disk_num,
                            "drive_letter": letter.strip().upper(),
                            "friendly_name": friendly_name
                        })
        except Exception as e:
            print(f"Error listing partitions: {e}")
        return partitions

    def get_default_target_drive_root(self):
        import os, re
        source_num = None
        if self.active_drive:
            m = re.search(r"PhysicalDrive(\d+)", self.active_drive, re.IGNORECASE)
            if m:
                source_num = int(m.group(1))
                
        source_letters = []
        if source_num is not None:
            try:
                import subprocess, json
                cmd = f'powershell -Command "Get-Partition -DiskNumber {source_num} | Select-Object -ExpandProperty DriveLetter | ConvertTo-Json"'
                res = subprocess.run(cmd, capture_output=True, text=True, shell=True)
                if res.returncode == 0 and res.stdout.strip():
                    data = json.loads(res.stdout.strip())
                    if isinstance(data, list):
                        source_letters = [str(x).upper() for x in data if x]
                    else:
                        source_letters = [str(data).upper()]
            except:
                pass

        for letter in "DEFGHIJKLMNOPQRSTUVWXYZ":
            if letter in source_letters:
                continue
            path = f"{letter}:\\"
            if os.path.exists(path):
                return path
        return "C:\\"

    def get_unscanned_segments(self, start_offset, end_offset):
        intervals = []
        if hasattr(self, "segment_progress") and self.segment_progress:
            with self.segment_lock:
                for seg_start, prog in self.segment_progress.items():
                    if prog > 0:
                        intervals.append((seg_start, seg_start + prog))
                        
        intervals.sort(key=lambda x: x[0])
        
        merged = []
        for start, end in intervals:
            if not merged:
                merged.append((start, end))
            else:
                last_start, last_end = merged[-1]
                if start <= last_end:
                    merged[-1] = (last_start, max(last_end, end))
                else:
                    merged.append((start, end))
                    
        unscanned = []
        curr = start_offset
        for start, end in merged:
            start = max(start_offset, min(end_offset, start))
            end = max(start_offset, min(end_offset, end))
            if start > curr:
                unscanned.append((curr, start))
            curr = max(curr, end)
            
        if curr < end_offset:
            unscanned.append((curr, end_offset))
            
        return unscanned

    def periodic_tree_refresh(self):
        if getattr(self, "tree_needs_update", False):
            # Do not clear/rebuild the treeview while actively scanning to prevent freezing
            is_active_scanning = self.is_scanning and not self.scan_paused
            if not is_active_scanning:
                if hasattr(self, "file_view") and self.file_view.winfo_viewable():
                    self.update_file_listbox_view()
                self.tree_needs_update = False
        self.after(1500, self.periodic_tree_refresh)

    def refresh_ui_widgets(self):
        self.all_files_btn.config(text=f"📁 Tüm Dosyalar ({self.total_recovered_count} - {self.format_size(self.total_recovered_size)})")
        for cat, val in self.category_counts.items():
            icon = CATEGORIES[cat]["icon"]
            cat_size = self.category_sizes[cat]
            self.sidebar_buttons[cat].config(text=f"{icon} {cat} ({val} - {self.format_size(cat_size)})")
            self.card_widgets[cat]["count_lbl"].config(text=f"{val} Dosya ({self.format_size(cat_size)})")

    def periodic_ui_refresh(self):
        import time
        self.gui_heartbeat = time.time()
        
        if getattr(self, "counters_need_update", False):
            self.refresh_ui_widgets()
            
            # Rate-limit folder gallery updates
            if hasattr(self, "folder_gallery_view") and self.folder_gallery_view.winfo_viewable() and self.current_gallery_folder is None:
                is_active_scanning = getattr(self, "is_scanning", False) and not getattr(self, "scan_paused", False)
                curr_time = time.time()
                last_update = getattr(self, "last_gallery_update_time", 0.0)
                if not is_active_scanning or (curr_time - last_update >= 3.0):
                    self.render_folder_gallery()
                    self.last_gallery_update_time = curr_time
                
            # Rate-limit detail map log tree updates
            if getattr(self, "detail_map_tree", None) and self.detail_map_tree.winfo_exists():
                self.populate_detail_map_tree(self.detail_map_tree)
                
            self.counters_need_update = False
            
        self.after(500, self.periodic_ui_refresh)


