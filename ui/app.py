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

from config import BG_DARK, SIDEBAR_BG, CONTENT_BG, TEXT_DARK, TEXT_GRAY, ACCENT_BLUE, TEXT_WHITE, CATEGORIES, FILE_SIGNATURES
from carver import read_raw_bytes_shared

from ui.drives import DrivesMixin
from ui.scan import ScanMixin
from ui.preview import PreviewMixin
from ui.export import ExportMixin
from ui.tree import TreeMixin
from ui.layout import LayoutMixin

class ConsoleRedirector:
    def __init__(self, app):
        self.app = app
        self.stdout = sys.stdout
        self.stderr = sys.stderr

    def write(self, message):
        if not message:
            return
        # Write to original standard streams (so they appear in IDE or parent processes)
        self.stdout.write(message)
        
        # Append to app log buffer
        self.app.console_logs.append(message)
        
        # Check if it contains traceback or error
        lower_msg = message.lower()
        if "error" in lower_msg or "exception" in lower_msg or "traceback" in lower_msg or "hata" in lower_msg:
            self.app.trigger_error_warning()
            
        # If the console window is currently open, write to it in real time
        if hasattr(self.app, "active_log_widget") and self.app.active_log_widget:
            try:
                self.app.active_log_widget.config(state="normal")
                self.app.active_log_widget.insert(tk.END, message)
                self.app.active_log_widget.config(state="disabled")
                self.app.active_log_widget.see(tk.END)
            except:
                pass

        # If the embedded dashboard log is active, write to it in real time
        if hasattr(self.app, "dash_log_text") and self.app.dash_log_text:
            try:
                self.app.dash_log_text.config(state="normal")
                self.app.dash_log_text.insert(tk.END, message)
                self.app.dash_log_text.config(state="disabled")
                self.app.dash_log_text.see(tk.END)
            except:
                pass

    def flush(self):
        self.stdout.flush()

class RecoveryApp(tk.Tk, DrivesMixin, ScanMixin, PreviewMixin, ExportMixin, TreeMixin, LayoutMixin):
    def __init__(self):
        super().__init__()
        
        # Console logging variables
        self.console_logs = []
        self.has_logged_error = False
        self.active_log_widget = None
        
        # Redirect stdout and stderr
        self.redirector = ConsoleRedirector(self)
        sys.stdout = self.redirector
        sys.stderr = self.redirector

        self.title("Disk Drill Style - Veri Kurtarma Paneli")
        self.geometry("1240x780")
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
        self.active_disk_handle = None
        self.active_drive = None
        
        # State variables
        self.is_scanning = False
        self.scan_paused = False
        self.scan_delay = 0.0  # Controls speed slider (0 = max speed, higher = more sleep)
        self.drives_map = {}
        self.drives_sizes_map = {}
        self.active_drive_size = 0
        self.resume_offset = 0
        self.elapsed_seconds = 0.0
        self.msg_queue = queue.Queue()
        self.selected_output_dir = os.path.abspath("kurtarilan_dosyalar")
        
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
        self.tree_item_map = {}
        self.folder_nodes = {}
        self.folder_stats = {}
        self.tree_reconstructed_node = None

        # Parallel and range scan variables
        self.use_parallel_var = tk.BooleanVar(value=False)
        self.worker_count_var = tk.StringVar(value="4")
        self.segment_size_gb_var = tk.StringVar(value="100")
        self.use_custom_range_var = tk.BooleanVar(value=False)
        self.custom_start_var = tk.StringVar(value="0")
        self.custom_end_var = tk.StringVar(value="100")
        self.custom_unit_var = tk.StringVar(value="GB")

        self.create_widgets()
        self.load_physical_drives()
        self.check_queue()
        self.check_for_resume_state()
        self.update_ram_usage()

        # Handle window closing to save state if scanning
        self.protocol("WM_DELETE_WINDOW", self.close_app)

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

    def close_app(self):
        if self.is_scanning:
            self.save_scan_state()
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
        while not self.msg_queue.empty() and processed < 100:
            processed += 1
            msg_type, data = self.msg_queue.get()
            if msg_type == "loaded_drives":
                self.drive_combo.config(values=data)
                if data:
                    self.drive_combo.current(0)
            elif msg_type == "status":
                self.scan_progress_lbl.config(text=data)
                self.status_lbl.config(text=data)
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
                self.lbl_speed_val.config(text=f"{speed:.2f} MB/s")
                self.lbl_elapsed_val.config(text=elapsed)
                self.lbl_eta_val.config(text=eta)
                self.draw_disk_map()
                
                status_text = f"Taranıyor: %{pct:.1f} | Hız: {speed:.2f} MB/s | Kalan: {eta}"
                self.scan_progress_lbl.config(text=status_text)
                self.status_lbl.config(text=status_text)
                
                # Auto-save every 5 seconds during active scanning
                import time
                curr_t = time.time()
                if curr_t - getattr(self, "last_save_time", 0.0) >= 5.0:
                    self.last_save_time = curr_t
                    self.save_scan_state()
            elif msg_type == "recovered_file_meta":
                self.virtual_files.append(data)
                self.update_ui_counters_fast(data)
                if self.file_view.winfo_viewable():
                    self.add_file_to_tree_view(data)
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
            elif msg_type == "video_status":
                self.vid_status_lbl.config(text=data)
                self.vid_play_btn.config(state="normal")
            elif msg_type == "video_error":
                self.vid_status_lbl.config(text=data)
                self.vid_play_btn.config(state="normal")
                messagebox.showerror("Hata", data)
            elif msg_type == "error":
                messagebox.showerror("Hata", data)
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
                
                # Delete state since scan is finished
                try:
                    if os.path.exists("scan_state.json"):
                        os.remove("scan_state.json")
                except:
                    pass
                
                self.scan_progress_lbl.config(text=data)
                self.status_lbl.config(text=data)
                messagebox.showinfo("Tarama Bitti", data)
                
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
            cat = "Diğer"
            
        self.all_files_btn.config(text=f"📁 Tüm Dosyalar ({self.total_recovered_count} - {self.format_size(self.total_recovered_size)})")
        
        icon = CATEGORIES[cat]["icon"]
        cat_val = self.category_counts[cat]
        cat_sz = self.category_sizes[cat]
        self.sidebar_buttons[cat].config(text=f"{icon} {cat} ({cat_val} - {self.format_size(cat_sz)})")
        self.card_widgets[cat]["count_lbl"].config(text=f"{cat_val} Dosya ({self.format_size(cat_sz)})")

    def reset_ui_counts(self):
        self.total_recovered_count = 0
        self.total_recovered_size = 0
        self.category_counts = {c: 0 for c in CATEGORIES.keys()}
        self.category_sizes = {c: 0 for c in CATEGORIES.keys()}
        
        self.all_files_btn.config(text="📁 Tüm Dosyalar (0)")
        for cat_name in CATEGORIES.keys():
            self.sidebar_buttons[cat_name].config(text=f"{CATEGORIES[cat_name]['icon']} {cat_name} (0)")
            self.card_widgets[cat_name]["count_lbl"].config(text="0 Dosya Bulundu")

    def trigger_error_warning(self):
        self.has_logged_error = True
        if hasattr(self, "log_btn"):
            self.log_btn.config(text="⚠️ Konsol Hatası!", bg="#FF4757")

    def show_console_log_window(self):
        # Create a new top-level log window
        log_win = tk.Toplevel(self)
        log_win.title("Konsol Log Akışı")
        log_win.geometry("700x500")
        log_win.configure(bg="#1E1E24")
        log_win.transient(self)
        
        title_lbl = tk.Label(log_win, text="Terminal Çıktısı & Log Akışı", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 12, "bold"))
        title_lbl.pack(anchor="w", padx=15, pady=10)
        
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


