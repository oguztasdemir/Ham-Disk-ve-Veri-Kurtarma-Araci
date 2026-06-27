# ui/gallery.py
import re
import os
import io
import sys
import time
import threading
import tkinter as tk
from tkinter import ttk, messagebox

try:
    from PIL import Image as PILImage, ImageTk
    HAS_PILLOW = True
except ImportError:
    HAS_PILLOW = False

class GalleryMixin:
    def init_folder_gallery_view(self):
        # State variables
        self.current_gallery_folder = None
        self.current_gallery_video_meta = None
        self.master_search_var = tk.StringVar()
        self.master_search_var.trace_add("write", lambda *args: self.on_master_search_change())
        self.gallery_search_var = tk.StringVar()
        self.gallery_search_var.trace_add("write", lambda *args: self.on_gallery_search_change())
        
        # Master frame inside content_frame
        self.folder_gallery_view = tk.Frame(self.content_frame, bg=self.content_bg)
        
        # Header bar
        header_bar = tk.Frame(self.folder_gallery_view, bg=self.content_bg, padx=20, pady=12, bd=1, relief="solid")
        header_bar.pack(fill=tk.X)
        
        back_btn = tk.Button(header_bar, text="◀ Gösterge Tablosuna Dön", command=self.show_dashboard_view, bg="#F1F2F6", fg=self.text_dark, borderwidth=0, padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        back_btn.pack(side=tk.LEFT)
        
        title_frame = tk.Frame(header_bar, bg=self.content_bg)
        title_frame.pack(side=tk.LEFT, padx=20)
        
        title_lbl = tk.Label(title_frame, text="🖼️ Klasör Galeri Modu", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 13, "bold"))
        title_lbl.pack(anchor="w")
        
        desc_lbl = tk.Label(title_frame, text="Sürücü seçerek bağımsız galeri taramasını başlatın. Bulunan klasörlerin detayları için 'Klasöre Git' demeniz yeterlidir.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8), wraplength=400, justify="left")
        desc_lbl.pack(anchor="w")
        
        # Gallery controls frame (Independent Scan Panel)
        self.gallery_ctrl_frame = tk.Frame(self.folder_gallery_view, bg=self.content_bg, padx=20, pady=10, bd=1, relief="ridge")
        self.gallery_ctrl_frame.pack(fill=tk.X)
        
        tk.Label(self.gallery_ctrl_frame, text="Kurtarılacak Diski Seçin:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        self.gallery_drive_var = tk.StringVar()
        self.gallery_drive_combo = ttk.Combobox(self.gallery_ctrl_frame, textvariable=self.gallery_drive_var, state="readonly", width=30)
        self.gallery_drive_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        self.gallery_start_btn = tk.Button(self.gallery_ctrl_frame, text="GALERİ TARAMASINI BAŞLAT", command=self.start_gallery_recovery, bg=self.accent_blue, fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=5, cursor="hand2")
        self.gallery_start_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.gallery_path_btn = tk.Button(self.gallery_ctrl_frame, text="Taşınacak Yeri Seçin", command=self.select_output_directory, bg="#F1F2F6", fg=self.text_dark, borderwidth=1, relief="solid", font=("Segoe UI", 9, "bold"), padx=12, pady=4, cursor="hand2")
        self.gallery_path_btn.pack(side=tk.LEFT, padx=(10, 10))
        
        self.gallery_pause_btn = tk.Button(self.gallery_ctrl_frame, text="DURAKLAT", command=self.pause_gallery_recovery, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=5, cursor="hand2")
        self.gallery_pause_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.gallery_resume_btn = tk.Button(self.gallery_ctrl_frame, text="DEVAM ET", command=self.resume_gallery_recovery, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=5, cursor="hand2")
        self.gallery_resume_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.gallery_backup_btn = tk.Button(self.gallery_ctrl_frame, text="💾 YEDEK AL", command=self.manual_gallery_backup, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=5, cursor="hand2")
        self.gallery_backup_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.gallery_close_session_btn = tk.Button(
            self.gallery_ctrl_frame, 
            text="Oturumu Kapat", 
            command=self.close_current_session, 
            bg="#FF4757", 
            fg=self.text_white, 
            borderwidth=0, 
            font=("Segoe UI", 9, "bold"), 
            padx=12, 
            pady=5, 
            cursor="hand2"
        )
        
        self.gallery_stop_btn = tk.Button(self.gallery_ctrl_frame, text="TARAMAYI DURDUR", command=self.stop_gallery_recovery, state="disabled", bg="#FF4757", fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=5, cursor="hand2")
        # self.gallery_stop_btn.pack(side=tk.LEFT, padx=(0, 15)) # Removed to hide the stop button per request
        
        self.gallery_progress_bar = ttk.Progressbar(self.gallery_ctrl_frame, orient="horizontal", mode="determinate", length=150)
        self.gallery_progress_bar.pack(side=tk.LEFT, padx=(0, 15))
        
        self.gallery_status_lbl = tk.Label(self.gallery_ctrl_frame, text="Hazır.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9))
        self.gallery_status_lbl.pack(side=tk.LEFT)
        
        self.gallery_show_adv_var = tk.BooleanVar(value=False)
        self.gallery_adv_btn = tk.Checkbutton(
            header_bar, 
            text="⚙️ Gelişmiş Ayarlar", 
            variable=self.gallery_show_adv_var, 
            command=self.toggle_gallery_adv_panel, 
            bg=self.content_bg, 
            fg=self.accent_blue, 
            activebackground=self.content_bg, 
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.gallery_adv_btn.pack(side=tk.RIGHT, padx=(15, 0))
        
        # Expandable advanced settings frame for Gallery Mode
        self.gallery_adv_frame = tk.Frame(self.folder_gallery_view, bg=self.content_bg, padx=20, pady=10, bd=1, relief="ridge")
        # Packed only when visible
        
        # Parallel scan options
        p_frame = tk.Frame(self.gallery_adv_frame, bg=self.content_bg)
        p_frame.pack(fill=tk.X, pady=5)
        
        self.gallery_parallel_cb = tk.Checkbutton(
            p_frame,
            text="Paralel Motorlar ile Parçalı Tara",
            variable=self.use_parallel_var,
            command=self.toggle_gallery_adv_options,
            bg=self.content_bg,
            fg=self.accent_blue,
            activebackground=self.content_bg,
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.gallery_parallel_cb.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(p_frame, text="Motor Sayısı (Thread):", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.gallery_worker_combo = ttk.Combobox(
            p_frame,
            textvariable=self.worker_count_var,
            values=[str(i) for i in range(1, 17)],
            state="disabled",
            width=5
        )
        self.gallery_worker_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        tk.Label(p_frame, text="Parça Boyutu (GB):", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(0, 5))
        self.gallery_segment_entry = tk.Entry(
            p_frame,
            textvariable=self.segment_size_gb_var,
            state="disabled",
            width=8
        )
        self.gallery_segment_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        # Custom range options
        r_frame = tk.Frame(self.gallery_adv_frame, bg=self.content_bg)
        r_frame.pack(fill=tk.X, pady=5)
        
        self.gallery_custom_range_cb = tk.Checkbutton(
            r_frame,
            text="Özel Bellek Aralığı Tara",
            variable=self.use_custom_range_var,
            command=self.toggle_gallery_adv_options,
            bg=self.content_bg,
            fg=self.accent_blue,
            activebackground=self.content_bg,
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.gallery_custom_range_cb.pack(side=tk.LEFT, padx=(0, 15))
        
        self.gallery_custom_block_lbl = tk.Label(r_frame, text="Blok Aralığı (1-100):", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold"))
        self.gallery_custom_block_lbl.pack(side=tk.LEFT, padx=(10, 5))
        
        self.gallery_custom_block_entry = tk.Entry(
            r_frame,
            textvariable=self.custom_block_range_var,
            state="disabled",
            width=10,
            font=("Segoe UI", 9, "bold")
        )
        self.gallery_custom_block_entry.pack(side=tk.LEFT, padx=(0, 10))

        
        self.gallery_scan_from_end_cb = tk.Checkbutton(
            r_frame,
            text="Sondan Ara",
            variable=self.scan_from_end_var,
            bg=self.content_bg,
            fg=self.accent_blue,
            activebackground=self.content_bg,
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.gallery_scan_from_end_cb.pack(side=tk.LEFT, padx=(15, 0))
        
        # Main Pane splits Left (Folders/Files List) and Right (In-App Preview Panel)
        self.gallery_pane = tk.PanedWindow(self.folder_gallery_view, orient=tk.HORIZONTAL, bg="#E4E5EA", sashwidth=4)
        self.gallery_pane.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (List/Grid browser)
        self.gallery_left_panel = tk.Frame(self.gallery_pane, bg=self.content_bg)
        self.gallery_pane.add(self.gallery_left_panel, minsize=500)
        
        # Right Panel (In-App Previews)
        self.gallery_preview_panel = tk.Frame(self.gallery_pane, bg=self.content_bg, padx=15, pady=15)
        self.gallery_pane.add(self.gallery_preview_panel, minsize=320)
        
        self.init_gallery_preview_widgets()
        
        # Master Search bar (contained in left panel)
        self.master_search_frame = tk.Frame(self.gallery_left_panel, bg=self.content_bg, padx=15, pady=10)
        self.master_search_frame.pack(fill=tk.X)
        
        tk.Label(self.master_search_frame, text="🔍 Klasör Ara:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        self.master_search_entry = tk.Entry(self.master_search_frame, textvariable=self.master_search_var, width=30, font=("Segoe UI", 9))
        self.master_search_entry.pack(side=tk.LEFT)
        
        # Past sessions list panel directly in Gallery Mode
        self.gallery_sessions_frame = tk.LabelFrame(
            self.gallery_left_panel, 
            text=" 💾 Kayıtlı Kurtarma Seansları (Yedekler) ", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 9, "bold"), 
            padx=15, 
            pady=10
        )
        self.gallery_sessions_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
        
        self.gallery_sessions_list = tk.Listbox(self.gallery_sessions_frame, bg="#F1F2F6", fg=self.text_dark, font=("Segoe UI", 9), height=3, selectbackground=self.accent_blue, borderwidth=1, relief="solid")
        self.gallery_sessions_list.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scroll = ttk.Scrollbar(self.gallery_sessions_frame, orient="vertical", command=self.gallery_sessions_list.yview)
        scroll.pack(side=tk.LEFT, fill=tk.Y)
        self.gallery_sessions_list.config(yscrollcommand=scroll.set)
        
        self.gallery_sessions_load_btn = tk.Button(
            self.gallery_sessions_frame, 
            text="Seçilen Yedeği Yükle", 
            command=self.load_gallery_selected_session, 
            bg=self.accent_blue, 
            fg=self.text_white, 
            activebackground="#006bce", 
            activeforeground=self.text_white, 
            borderwidth=0, 
            font=("Segoe UI", 9, "bold"), 
            padx=12, 
            pady=8,
            cursor="hand2"
        )
        self.gallery_sessions_load_btn.pack(side=tk.RIGHT, padx=(15, 0))
        
        # Scrollable Canvas for Gallery cards inside Left Panel
        self.gallery_container = tk.Frame(self.gallery_left_panel, bg=self.content_bg)
        self.gallery_container.pack(fill=tk.BOTH, expand=True, padx=15, pady=5)
        
        self.gallery_canvas = tk.Canvas(self.gallery_container, bg=self.content_bg, borderwidth=0, highlightthickness=0)
        self.gallery_scrollbar = ttk.Scrollbar(self.gallery_container, orient="vertical", command=self.gallery_canvas.yview)
        
        self.gallery_scrollable_frame = tk.Frame(self.gallery_canvas, bg=self.content_bg)
        self.gallery_scrollable_frame.bind(
            "<Configure>",
            lambda e: self.gallery_canvas.configure(
                scrollregion=self.gallery_canvas.bbox("all")
            )
        )
        
        self.gallery_canvas_window = self.gallery_canvas.create_window((0, 0), window=self.gallery_scrollable_frame, anchor="nw")
        
        def _on_canvas_configure(event):
            self.gallery_canvas.itemconfigure(self.gallery_canvas_window, width=event.width)
            
        self.gallery_canvas.bind('<Configure>', _on_canvas_configure)
        self.gallery_canvas.configure(yscrollcommand=self.gallery_scrollbar.set)
        
        self.gallery_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        self.gallery_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind Mousewheel
        def _on_mousewheel(event):
            if self.folder_gallery_view.winfo_viewable():
                self.gallery_canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        self.gallery_canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        # Maps for UI mapping and PhotoImage caching
        self.gallery_labels = {}
        self.gallery_detail_labels = {}
        self.gallery_photos = {}
        self.gallery_tree_item_map = {}

    def toggle_gallery_adv_panel(self):
        if self.gallery_show_adv_var.get():
            self.gallery_adv_frame.pack(fill=tk.X, before=self.gallery_pane, pady=(5, 10))
            self.toggle_gallery_adv_options()
        else:
            self.gallery_adv_frame.pack_forget()

    def toggle_gallery_adv_options(self):
        is_active_scanning = getattr(self, "is_scanning", False) and not getattr(self, "scan_paused", False)
        if is_active_scanning:
            # Disable inputs mid-scan only if actively scanning (not paused)
            self.gallery_parallel_cb.config(state="disabled")
            self.gallery_worker_combo.config(state="disabled")
            self.gallery_segment_entry.config(state="disabled")
            self.gallery_custom_range_cb.config(state="disabled")
            self.gallery_custom_block_entry.config(state="disabled")
            if hasattr(self, "gallery_unscanned_cb"):
                self.gallery_unscanned_cb.config(state="disabled")
            if hasattr(self, "gallery_scan_from_end_cb"):
                self.gallery_scan_from_end_cb.config(state="disabled")
        else:
            self.gallery_parallel_cb.config(state="normal")
            self.gallery_custom_range_cb.config(state="normal")
            if hasattr(self, "gallery_unscanned_cb"):
                self.gallery_unscanned_cb.config(state="normal")
            if hasattr(self, "gallery_scan_from_end_cb"):
                self.gallery_scan_from_end_cb.config(state="normal")
            
            state = "normal" if self.use_parallel_var.get() else "disabled"
            self.gallery_worker_combo.config(state=state if state == "disabled" else "readonly")
            self.gallery_segment_entry.config(state=state)
            
            range_state = "normal" if self.use_custom_range_var.get() else "disabled"
            self.gallery_custom_block_entry.config(state=range_state)

    def populate_gallery_sessions(self):
        if not hasattr(self, "gallery_sessions_list") or not self.gallery_sessions_list:
            return
            
        self.gallery_sessions_list.delete(0, tk.END)
        self.gallery_session_files_map = {}
        
        import os
        import json
        
        if not os.path.exists("yedekler"):
            return
            
        session_files = []
        for item in os.listdir("yedekler"):
            item_path = os.path.join("yedekler", item)
            if os.path.isdir(item_path):
                for subfile in os.listdir(item_path):
                    if subfile.startswith("session_") and subfile.endswith(".json"):
                        session_files.append(os.path.join(item_path, subfile))
            elif item.startswith("session_") and item.endswith(".json"):
                session_files.append(item_path)
                
        # Filter backups to only show the ones belonging to the current session, if one is active
        current_session = getattr(self, "current_session_file", None)
        if current_session:
            curr_dir = os.path.dirname(os.path.abspath(current_session))
            filtered_files = []
            for s_file in session_files:
                s_abspath = os.path.abspath(s_file)
                if os.path.dirname(s_abspath) == curr_dir or s_abspath == os.path.abspath(current_session):
                    filtered_files.append(s_file)
            session_files = filtered_files
            
        # Sort sessions by date (newest first)
        session_files.sort(reverse=True)
        
        for idx, s_file in enumerate(session_files):
            try:
                with open(s_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                timestamp = data.get("timestamp", "")
                drive = data.get("active_drive", "Bilinmeyen")
                if "PhysicalDrive" in drive:
                    drive_num = drive.split("PhysicalDrive")[-1]
                    drive = f"Disk {drive_num}"
                else:
                    drive = os.path.basename(drive)
                    
                v_files = data.get("virtual_files", [])
                total_files = len(v_files)
                exported_files = sum(1 for x in v_files if x.get("exported", False))
                
                display_str = f"{timestamp} | {drive} | Kurtarılan: {exported_files} / {total_files}"
                self.gallery_sessions_list.insert(tk.END, display_str)
                self.gallery_session_files_map[idx] = (s_file, data)
            except Exception as e:
                print(f"Error reading session {s_file}: {e}")
 
    def load_gallery_selected_session(self):
        selected_indices = self.gallery_sessions_list.curselection()
        if not selected_indices:
            messagebox.showwarning("Uyarı", "Lütfen yüklemek istediğiniz yedeği listeden seçin!")
            return
            
        idx = selected_indices[0]
        if idx in self.gallery_session_files_map:
            s_file, data = self.gallery_session_files_map[idx]
            ok = self.load_selected_session(s_file, data)
            if ok is False:
                self.populate_gallery_sessions()
                return
            self.render_folder_gallery()
            messagebox.showinfo("Başarılı", "Seçilen yedek seansı başarıyla yüklendi!")

    def init_gallery_preview_widgets(self):
        # Dedicated preview panel layout
        self.gallery_preview_title = tk.Label(self.gallery_preview_panel, text="BELLEK ÖNİZLEME", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 11, "bold"))
        self.gallery_preview_title.pack(anchor="w", pady=(0, 8))
        
        self.gallery_preview_canvas = tk.Canvas(self.gallery_preview_panel, bg="#F1F2F6", highlightthickness=1, highlightbackground="#DCDDE1")
        self.gallery_preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Video controls
        self.gallery_preview_video_frame = tk.Frame(self.gallery_preview_panel, bg="#F1F2F6", bd=1, relief="solid", padx=15, pady=20)
        
        vid_container = tk.Frame(self.gallery_preview_video_frame, bg="#F1F2F6")
        vid_container.pack(fill=tk.BOTH, expand=True)
        
        vid_screen_container = tk.Frame(vid_container, width=280, height=200, bg="#000000")
        vid_screen_container.pack_propagate(False)
        vid_screen_container.pack(pady=10)
        
        self.gallery_vid_screen = tk.Label(vid_screen_container, bg="#000000", fg=self.accent_blue, text="📺 Video Hazır", font=("Segoe UI", 16, "bold"), cursor="hand2")
        self.gallery_vid_screen.pack(fill=tk.BOTH, expand=True)
        
        self.gallery_vid_info_lbl = tk.Label(vid_container, text="Video Yükleniyor...", bg="#F1F2F6", fg=self.text_dark, font=("Segoe UI", 9, "bold"), justify="center", wraplength=260)
        self.gallery_vid_info_lbl.pack(pady=5)
        
        self.gallery_vid_timeline = tk.Scale(vid_container, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False, bg="#F1F2F6", highlightthickness=0, bd=0, sliderlength=15, width=10, cursor="sb_h_double_arrow")
        self.gallery_vid_timeline.pack(fill=tk.X, padx=5, pady=2)
        
        self.gallery_vid_time_lbl = tk.Label(vid_container, text="00:00 / 00:00", bg="#F1F2F6", fg=self.text_dark, font=("Segoe UI", 9, "bold"))
        self.gallery_vid_time_lbl.pack(pady=2)
        
        controls_frame = tk.Frame(vid_container, bg="#F1F2F6")
        controls_frame.pack(pady=5)
        
        self.gallery_vid_play_pause_btn = tk.Button(controls_frame, text="▶", command=self.toggle_gallery_video_play_pause, bg=self.accent_blue, fg=self.text_white, font=("Segoe UI", 10, "bold"), width=3, borderwidth=0, cursor="hand2")
        self.gallery_vid_play_pause_btn.pack(side=tk.LEFT, padx=2)
        
        self.gallery_vid_stop_btn = tk.Button(controls_frame, text="⏹", command=self.stop_gallery_video_preview, bg="#FF4757", fg=self.text_white, font=("Segoe UI", 10, "bold"), width=3, borderwidth=0, cursor="hand2")
        self.gallery_vid_stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.gallery_vid_mute_btn = tk.Button(controls_frame, text="🔊", command=self.toggle_gallery_video_mute, bg="#CED6E0", fg=self.text_dark, font=("Segoe UI", 10, "bold"), width=3, borderwidth=0, cursor="hand2")
        self.gallery_vid_mute_btn.pack(side=tk.LEFT, padx=(10, 2))
        
        self.gallery_vid_volume_scale = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False, bg="#F1F2F6", highlightthickness=0, bd=0, sliderlength=12, width=8, length=70, cursor="hand2")
        self.gallery_vid_volume_scale.set(70)
        self.gallery_vid_volume_scale.pack(side=tk.LEFT, padx=2)
        
        self.gallery_vid_status_lbl = tk.Label(vid_container, text="Oynatmaya hazır.", bg="#F1F2F6", fg=self.text_gray, font=("Segoe UI", 9, "italic"))
        self.gallery_vid_status_lbl.pack(pady=5)

    def show_folder_gallery_view(self):
        self.dashboard_view.pack_forget()
        if hasattr(self, "file_view") and self.file_view:
            self.file_view.pack_forget()
        self.folder_gallery_view.pack(fill=tk.BOTH, expand=True)
        
        self.current_gallery_folder = None
        self.master_search_var.set("")
        self.gallery_search_var.set("")
        self.stop_gallery_video_preview()
        self.reset_gallery_preview_panel()
        self.render_folder_gallery()
        if hasattr(self, "log_btn"):
            self.log_btn.lift()
        if hasattr(self, "top_status_frame") and self.top_status_frame.winfo_manager():
            self.top_status_frame.lift()

    def start_gallery_recovery(self):
        if getattr(self, "is_scanning", False):
            selected_disp = self.gallery_drive_var.get()
            target_drive = self.drives_map.get(selected_disp)
            if target_drive and target_drive == self.active_drive:
                self.resume_gallery_recovery()
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
            
        selected_disp = self.gallery_drive_var.get()
        if not selected_disp or selected_disp == "Diskler aranıyor...":
            messagebox.showwarning("Uyarı", "Lütfen kurtarma yapmak istediğiniz diski seçin!")
            return
            
        if "seagate" not in selected_disp.lower():
            messagebox.showerror(
                "Kritik Hata: Uyumsuz Sürücü!",
                "Hata: Seçilen sürücü Seagate marka değil!\n\n"
                "Veri kurtarma işleminin yalnızca Seagate disk üzerinden yapılması planlanmıştır. "
                "Lütfen doğru sürücüyü seçtiğinizden emin olun."
            )
            return
            
        self.active_drive = self.drives_map.get(selected_disp)
        self.active_drive_size = self.drives_sizes_map.get(selected_disp, 0)
        if not self.active_drive:
            messagebox.showerror("Hata", "Sürücü yolu tespit edilemedi.")
            return

        if not getattr(self, "current_session_file", None):
            ok = self.setup_new_session_flow()
            if not ok:
                # User cancelled or invalid selection
                self.is_scanning = False
                self.scan_paused = False
                self.gallery_start_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
                self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                self.gallery_backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
                return
                
        if self.is_same_disk(self.active_drive, self.selected_output_dir):
            messagebox.showerror(
                "Kritik Hata: Aynı Disk!", 
                "Hata: Kurtarma yapmak istediğiniz hedef disk ile kaynak disk aynı fiziksel disk üzerindedir!\n\n"
                "Verilerin üst üste yazılmasını (overwrite) ve veri kaybını önlemek için lütfen kurtarma konumunu değiştirin."
            )
            self.current_session_file = None
            return

        self.scan_source = "gallery"
        self.is_scanning = True
        self.scan_paused = False
        
        self.gallery_start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_pause_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_stop_btn.config(state="normal")
        
        self.virtual_files.clear()
        self.reset_ui_counts()
        
        # Reset stats
        self.resume_offset = 0
        self.elapsed_seconds = 0.0
        self.gallery_progress_bar.config(value=0)
        
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
            try:
                range_str = self.custom_block_range_var.get().strip()
                if "-" in range_str:
                    s_part, e_part = range_str.split("-", 1)
                    start_block = int(s_part.strip())
                    end_block = int(e_part.strip())
                else:
                    start_block = int(range_str)
                    end_block = start_block
                
                start_block = max(1, min(100, start_block))
                end_block = max(start_block, min(100, end_block))
                
                start_offset = int((start_block - 1) * (self.active_drive_size / 100))
                end_offset = int(end_block * (self.active_drive_size / 100))
                
                start_offset = (start_offset // 512) * 512
                end_offset = (end_offset // 512) * 512
            except Exception as e:
                print(f"Error parsing custom block range: {e}")
                
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
            if not hasattr(self, "segment_bounds"):
                self.segment_bounds = {}
            offset = start_offset
            while offset < end_offset:
                end = min(offset + segment_size_bytes, end_offset)
                self.scan_segments.append((offset, end))
                self.segment_progress[offset] = 0
                self.segment_bounds[offset] = end
                offset = end
        else:
            worker_count = 1
            self.scan_segments = [(start_offset, end_offset)]
            self.segment_progress[start_offset] = 0
            if not hasattr(self, "segment_bounds"):
                self.segment_bounds = {}
            self.segment_bounds[start_offset] = end_offset
            
        self.active_worker_count = worker_count
        
        from config import FILE_SIGNATURES
        # Only JPEGs and PNGs are requested to find valid images
        active_sigs = [sig for sig in FILE_SIGNATURES.values() if sig["category"] == "Resim"]
        
        self.gallery_status_lbl.config(text="Galeri taraması başlatıldı...")
        
        from carver import scan_disk_worker
        for _ in range(worker_count):
            threading.Thread(target=scan_disk_worker, name="GalleryScanWorker", args=(self, self.active_drive, active_sigs), daemon=True).start()

    def pause_gallery_recovery(self):
        self.scan_paused = True
        self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_resume_btn.config(state="normal", bg=self.accent_blue, fg=self.text_white)
        self.gallery_start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_backup_btn.config(state="normal", bg="#FF9F43", fg=self.text_white)
        self.gallery_status_lbl.config(text="Tarama duraklatıldı.")
        self.save_scan_state()

    def resume_gallery_recovery(self):
        self.scan_paused = False
        self.gallery_pause_btn.config(state="normal", bg="#FF4757", fg=self.text_white)
        self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_start_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_backup_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_status_lbl.config(text="Tarama devam ediyor...")
        self.last_auto_export_time = time.time() # Reset 5-minute timer
        if hasattr(self, "toggle_gallery_adv_options"):
            self.toggle_gallery_adv_options()
        self.ensure_gallery_worker_threads_running()
            
    def manual_gallery_backup(self):
        self.gallery_status_lbl.config(text="Yedekleniyor...")
        self.save_scan_state()
        self.auto_export_unexported()

    def ensure_gallery_worker_threads_running(self):
        # Check if threads are already running
        running = any(t.name == "GalleryScanWorker" and t.is_alive() for t in threading.enumerate())
        if running:
            return
            
        from config import FILE_SIGNATURES
        active_sigs = [sig for sig in FILE_SIGNATURES.values() if sig["category"] == "Resim"]
        
        self.scan_start_offset = getattr(self, "scan_start_offset", 0)
        self.scan_end_offset = getattr(self, "scan_end_offset", self.active_drive_size)
        
        if not getattr(self, "scan_segments", None) or getattr(self, "scan_paused", False):
            try:
                segment_size_gb = float(self.segment_size_gb_var.get())
            except:
                segment_size_gb = 100.0
            segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)
            
            start_offset = 0
            end_offset = self.active_drive_size
            
            if self.use_custom_range_var.get():
                try:
                    range_str = self.custom_block_range_var.get().strip()
                    if "-" in range_str:
                        s_part, e_part = range_str.split("-", 1)
                        start_block = int(s_part.strip())
                        end_block = int(e_part.strip())
                    else:
                        start_block = int(range_str)
                        end_block = start_block
                    
                    start_block = max(1, min(100, start_block))
                    end_block = max(start_block, min(100, end_block))
                    
                    start_offset = int((start_block - 1) * (self.active_drive_size / 100))
                    end_offset = int(end_block * (self.active_drive_size / 100))
                    
                    start_offset = (start_offset // 512) * 512
                    end_offset = (end_offset // 512) * 512
                except Exception as e:
                    print(f"Error parsing custom block range: {e}")
                    
            start_offset = max(0, min(self.active_drive_size, start_offset))
            end_offset = max(start_offset, min(self.active_drive_size, end_offset))
            
            self.scan_start_offset = start_offset
            self.scan_end_offset = end_offset
            
            if not getattr(self, "segment_progress", None):
                self.segment_progress = {}
            if not getattr(self, "segment_lock", None):
                self.segment_lock = threading.Lock()
                
            self.scan_segments = []
            
            # Always get unscanned intervals to prevent scanning already scanned segments
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
        
        from carver import scan_disk_worker
        for _ in range(worker_count):
            threading.Thread(target=scan_disk_worker, name="GalleryScanWorker", args=(self, self.active_drive, active_sigs), daemon=True).start()

    def stop_gallery_recovery(self):
        self.is_scanning = False
        self.scan_paused = False
        self.gallery_status_lbl.config(text="Tarama durduruldu.")
        self.gallery_start_btn.config(state="normal")
        self.gallery_stop_btn.config(state="disabled")
        self.gallery_pause_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.gallery_resume_btn.config(state="disabled", bg="#CED6E0", fg=self.text_gray)
        self.save_scan_state()
        self.auto_export_unexported()

    def reset_gallery_preview_panel(self):
        self.gallery_preview_video_frame.pack_forget()
        self.gallery_preview_canvas.pack(fill=tk.BOTH, expand=True)
        self.gallery_preview_canvas.delete("all")
        self.gallery_preview_title.config(text="BELLEK ÖNİZLEME")
        self.gallery_preview_canvas.create_text(20, 30, anchor="nw", fill=self.text_dark, text="Önizlemek için listeden bir dosya seçin.", font=("Segoe UI", 10, "italic"))

    def render_folder_gallery(self):
        # Update session list box
        self.populate_gallery_sessions()
        
        if not hasattr(self, "gallery_cards"):
            self.gallery_cards = {}
            
        if self.current_gallery_folder is None:
            self.master_search_frame.pack(fill=tk.X)
            if hasattr(self, "gallery_sessions_frame") and self.gallery_sessions_frame:
                if self.is_scanning:
                    self.gallery_sessions_frame.pack_forget()
                else:
                    self.gallery_sessions_frame.pack(fill=tk.X, padx=15, pady=(5, 10))
                
            if not self.virtual_files:
                for widget in self.gallery_scrollable_frame.winfo_children():
                    widget.destroy()
                self.gallery_labels.clear()
                self.gallery_detail_labels.clear()
                self.gallery_photos.clear()
                self.gallery_cards.clear()
                self.gallery_tree_item_map.clear()
                
                no_lbl = tk.Label(self.gallery_scrollable_frame, text="Henüz aktif tarama dosyası yok. Yukarıdan tarama başlatabilir veya kayıtlı yedekler listesinden bir yedek yükleyebilirsiniz.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 11, "italic"), pady=50)
                no_lbl.pack()
                return
            self.render_master_gallery()
        else:
            # Detail view: clear everything and build detail view
            for widget in self.gallery_scrollable_frame.winfo_children():
                widget.destroy()
            self.gallery_labels.clear()
            self.gallery_detail_labels.clear()
            # Do NOT clear self.gallery_photos, to keep cached PhotoImages
            self.gallery_tree_item_map.clear()
            self.gallery_cards.clear()
            
            self.master_search_frame.pack_forget()
            if hasattr(self, "gallery_sessions_frame") and self.gallery_sessions_frame:
                self.gallery_sessions_frame.pack_forget()
            self.render_detail_gallery()

    def render_master_gallery(self):
        self.reset_gallery_preview_panel()
        
        # Group virtual files by folder path
        folders = {}
        for f in self.virtual_files:
            # Gallery mode only displays previewable files (images and videos)
            if f["ext"].lower() not in [".jpg", ".jpeg", ".png", ".mp4"]:
                continue
                
            if f.get("custom_path"):
                path_str = f["custom_path"]
            else:
                path_str = f["category"]
            folders.setdefault(path_str, []).append(f)
            
        # Filter folders list by master search query
        query = self.master_search_var.get().lower().strip()
        filtered_folders = {k: v for k, v in folders.items() if query in k.lower()}
        
        if not filtered_folders:
            # Clean up all existing cards
            if hasattr(self, "gallery_cards"):
                for path_str, card_info in list(self.gallery_cards.items()):
                    try: card_info["card"].destroy()
                    except: pass
                self.gallery_cards.clear()
            
            # Clean up other child elements
            for child in self.gallery_scrollable_frame.winfo_children():
                try: child.destroy()
                except: pass
                
            no_match_lbl = tk.Label(self.gallery_scrollable_frame, text="Arama kriterine uygun klasör bulunamadı.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 10, "italic"), pady=20)
            no_match_lbl.pack()
            return
            
        cols_count = 2
        thumbnail_requests = {}
        
        self.gallery_cards = getattr(self, "gallery_cards", {})
        
        # 1. Clean up obsolete cards
        for path_str in list(self.gallery_cards.keys()):
            if path_str not in filtered_folders:
                try:
                    self.gallery_cards[path_str]["card"].destroy()
                except:
                    pass
                del self.gallery_cards[path_str]
                
        # 2. Clean up non-card child widgets (like old status labels or previous messages)
        card_frames = {c_info["card"] for c_info in self.gallery_cards.values()}
        for child in self.gallery_scrollable_frame.winfo_children():
            if child not in card_frames:
                try: child.destroy()
                except: pass
                
        # 3. Create or update cards
        for idx, (path_str, files) in enumerate(filtered_folders.items()):
            r = idx // cols_count
            c = idx % cols_count
            
            total_size_bytes = sum(x["size"] for x in files)
            size_str = self.format_size(total_size_bytes)
            
            previews = [f for f in files if f["ext"].lower() in [".jpg", ".jpeg", ".png", ".mp4"]][:5]
            if len(previews) < 5:
                previews += [f for f in files if f not in previews][:5 - len(previews)]
                
            if path_str in self.gallery_cards:
                # Update existing card
                card_info = self.gallery_cards[path_str]
                card = card_info["card"]
                card.grid(row=r, column=c, padx=12, pady=12, sticky="nsew")
                card_info["stats_lbl"].config(text=f"{len(files)} dosya | {size_str}")
                
                # Check if preview files changed
                old_previews = card_info.get("slot_files", [])
                previews_changed = (len(old_previews) != len(previews) or 
                                    any(old_previews[i]["id"] != previews[i]["id"] for i in range(len(previews))))
                
                slots = card_info["slots"]
                if previews_changed:
                    for i in range(5):
                        lbl_slot = slots[i]
                        if i < len(previews):
                            f = previews[i]
                            ext = f["ext"].lower()
                            default_icon = "🎬" if ext == ".mp4" else ("📄" if ext not in [".jpg", ".jpeg", ".png"] else "📁")
                            
                            slot_key = f"card_{path_str}_{f['id']}"
                            photo = self.gallery_photos.get(slot_key)
                            if photo:
                                lbl_slot.config(image=photo, text="", width=0, height=0)
                            else:
                                lbl_slot.config(image="", text=default_icon, font=("Segoe UI", 12), bg="#DFE4EA", width=3, height=1)
                                if ext in [".jpg", ".jpeg", ".png"]:
                                    self.gallery_labels[slot_key] = lbl_slot
                                    thumbnail_requests.setdefault(path_str, []).append(f)
                        else:
                            lbl_slot.config(image="", text="", bg="#DFE4EA", width=3, height=1)
                    card_info["slot_files"] = previews
                else:
                    # Sync any newly loaded thumbnails from cache
                    for i in range(len(previews)):
                        f = previews[i]
                        if f["ext"].lower() in [".jpg", ".jpeg", ".png"]:
                            slot_key = f"card_{path_str}_{f['id']}"
                            photo = self.gallery_photos.get(slot_key)
                            if photo:
                                slots[i].config(image=photo, text="", width=0, height=0)
            else:
                # Create Card frame
                card = tk.Frame(self.gallery_scrollable_frame, bg="#F1F2F6", bd=1, relief="solid", padx=12, pady=12, width=250, height=270)
                card.grid(row=r, column=c, padx=12, pady=12, sticky="nsew")
                card.grid_propagate(False)
                
                # Title
                path_lbl = tk.Label(card, text=path_str, font=("Segoe UI", 9, "bold"), bg="#F1F2F6", fg=self.text_dark, wraplength=220, height=2, anchor="center")
                path_lbl.pack(fill=tk.X)
                
                # Stats
                stats_lbl = tk.Label(card, text=f"{len(files)} dosya | {size_str}", font=("Segoe UI", 8), bg="#F1F2F6", fg=self.text_gray)
                stats_lbl.pack(pady=(2, 8))
                
                # 5-Item preview row directly inside card
                thumb_container = tk.Frame(card, bg="#F1F2F6")
                thumb_container.pack(pady=5)
                
                slots_list = []
                # Draw slots
                for i in range(5):
                    if i < len(previews):
                        f = previews[i]
                        ext = f["ext"].lower()
                        default_icon = "🎬" if ext == ".mp4" else ("📄" if ext not in [".jpg", ".jpeg", ".png"] else "📁")
                    else:
                        default_icon = ""
                        
                    lbl_slot = tk.Label(thumb_container, text=default_icon, font=("Segoe UI", 12), bg="#DFE4EA", relief="flat", width=3, height=1)
                    lbl_slot.pack(side=tk.LEFT, padx=3)
                    slots_list.append(lbl_slot)
                    
                    if i < len(previews):
                        f = previews[i]
                        if f["ext"].lower() in [".jpg", ".jpeg", ".png"]:
                            slot_key = f"card_{path_str}_{f['id']}"
                            photo = self.gallery_photos.get(slot_key)
                            if photo:
                                lbl_slot.config(image=photo, text="", width=0, height=0)
                            else:
                                self.gallery_labels[slot_key] = lbl_slot
                                thumbnail_requests.setdefault(path_str, []).append(f)
                
                # Action button
                go_btn = tk.Button(
                    card, 
                    text="Klasöre Git", 
                    command=lambda p=path_str: self.open_folder(p), 
                    bg=self.accent_blue, 
                    fg=self.text_white, 
                    activebackground="#006bce", 
                    activeforeground=self.text_white, 
                    borderwidth=0, 
                    font=("Segoe UI", 9, "bold"), 
                    pady=5,
                    cursor="hand2"
                )
                go_btn.pack(fill=tk.X, side=tk.BOTTOM)
                
                # Click card bindings to open folder
                def open_folder(event, p=path_str):
                    self.open_folder(p)
                    
                for w in (card, path_lbl, stats_lbl, thumb_container):
                    w.bind("<Button-1>", open_folder)
                    w.config(cursor="hand2")
                    
                # Dynamic Hover
                def on_enter(event, current_card=card, widgets=[card, path_lbl, stats_lbl, thumb_container]):
                    current_card.config(bg="#E4E5EA", highlightbackground=self.accent_blue, highlightcolor=self.accent_blue, highlightthickness=1)
                    for w in widgets:
                        w.config(bg="#E4E5EA")
                        
                def on_leave(event, current_card=card, widgets=[card, path_lbl, stats_lbl, thumb_container]):
                    current_card.config(bg="#F1F2F6", highlightthickness=0)
                    for w in widgets:
                        w.config(bg="#F1F2F6")
                        
                card.bind("<Enter>", on_enter)
                card.bind("<Leave>", on_leave)
                
                self.gallery_cards[path_str] = {
                    "card": card,
                    "path_lbl": path_lbl,
                    "stats_lbl": stats_lbl,
                    "thumb_container": thumb_container,
                    "slots": slots_list,
                    "slot_files": previews
                }
                
        # Start background card thumbnail loader only if we have new request items
        if thumbnail_requests:
            threading.Thread(target=self._async_load_card_thumbnails, args=(thumbnail_requests,), daemon=True).start()

    def open_folder(self, folder_path):
        self.current_gallery_folder = folder_path
        self.gallery_search_var.set("")
        self.render_folder_gallery()

    def render_detail_gallery(self):
        self.reset_gallery_preview_panel()
        
        # 1. Back button & Title Header
        header_frame = tk.Frame(self.gallery_scrollable_frame, bg=self.content_bg)
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        back_btn = tk.Button(
            header_frame, 
            text="◀ Klasörlere Dön", 
            command=self.back_to_master_gallery, 
            bg="#2F3542", 
            fg=self.text_white, 
            borderwidth=0, 
            padx=10, 
            pady=5, 
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        back_btn.pack(side=tk.LEFT)
        
        folder_files = []
        for f in self.virtual_files:
            # Gallery mode only displays previewable files (images and videos)
            if f["ext"].lower() not in [".jpg", ".jpeg", ".png", ".mp4"]:
                continue
                
            if f.get("custom_path"):
                path_str = f["custom_path"]
            else:
                path_str = f["category"]
            if path_str == self.current_gallery_folder:
                folder_files.append(f)
                
        self.gallery_detail_lbl = tk.Label(
            header_frame, 
            text=f"Klasör İçeriği: {self.current_gallery_folder} ({len(folder_files)} dosya)", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 12, "bold")
        )
        self.gallery_detail_lbl.pack(side=tk.LEFT, padx=15)
        
        recover_btn = tk.Button(
            header_frame, 
            text="Bu Klasördekileri Geri Getir", 
            command=lambda: self.save_files_to_disk(folder_files), 
            bg=self.accent_blue, 
            fg=self.text_white, 
            borderwidth=0, 
            padx=15, 
            pady=5, 
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        recover_btn.pack(side=tk.RIGHT)
        
        # 2. Search bar
        search_frame = tk.Frame(self.gallery_scrollable_frame, bg=self.content_bg, pady=5)
        search_frame.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(search_frame, text="🔍 Klasör İçindekileri Ara:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        
        search_ent = tk.Entry(search_frame, textvariable=self.gallery_search_var, width=30, font=("Segoe UI", 10))
        search_ent.pack(side=tk.LEFT)
        search_ent.focus_set()
        
        # 3. Preview Row (Up to 5 representative items)
        preview_row_frame = tk.LabelFrame(
            self.gallery_scrollable_frame, 
            text=" Örnek Önizlemeler (En Fazla 5 Öğe) ", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 10, "bold"), 
            padx=10, 
            pady=10
        )
        preview_row_frame.pack(fill=tk.X, pady=(0, 20))
        
        previews = [f for f in folder_files if f["ext"].lower() in [".jpg", ".jpeg", ".png", ".mp4"]][:5]
        if len(previews) < 5:
            remaining = [f for f in folder_files if f not in previews]
            previews += remaining[:5 - len(previews)]
            
        self.gallery_detail_labels = {}
        
        for i, f in enumerate(previews):
            item_frame = tk.Frame(preview_row_frame, bg="#F1F2F6", bd=1, relief="solid", width=140, height=150)
            item_frame.grid(row=0, column=i, padx=10, pady=5)
            item_frame.grid_propagate(False)
            
            ext = f["ext"].lower()
            icon = "🎬" if ext == ".mp4" else ("📄" if ext not in [".jpg", ".jpeg", ".png"] else "📁")
            
            lbl_thumb = tk.Label(item_frame, text=icon, font=("Segoe UI", 28), bg="#F1F2F6", fg=self.accent_blue)
            lbl_thumb.pack(pady=(10, 5))
            
            if ext in [".jpg", ".jpeg", ".png"]:
                self.gallery_detail_labels[f["id"]] = lbl_thumb
                
            name_lbl = tk.Label(item_frame, text=f["name"], font=("Segoe UI", 8), bg="#F1F2F6", fg=self.text_dark, wraplength=120, height=2)
            name_lbl.pack(fill=tk.X)
            
            size_lbl = tk.Label(item_frame, text=self.format_size(f["size"]), font=("Segoe UI", 7), bg="#F1F2F6", fg=self.text_gray)
            size_lbl.pack()
            
            # Click preview items to load in preview pane
            def preview_click(event, target_file=f):
                self.preview_selected_gallery_file(target_file)
                
            for w in (item_frame, lbl_thumb, name_lbl, size_lbl):
                w.bind("<Button-1>", preview_click)
                w.config(cursor="hand2")
                
        # Trigger async previews thread
        threading.Thread(target=self._async_load_detail_previews, args=(previews,), daemon=True).start()
        
        # 4. Treeview
        tree_section = tk.LabelFrame(
            self.gallery_scrollable_frame, 
            text=" Klasördeki Tüm Dosyalar ", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 10, "bold"), 
            padx=10, 
            pady=10
        )
        tree_section.pack(fill=tk.BOTH, expand=True)
        
        tree_container = tk.Frame(tree_section, bg=self.content_bg)
        tree_container.pack(fill=tk.BOTH, expand=True)
        
        scroll_y = ttk.Scrollbar(tree_container, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        style = ttk.Style()
        style.configure("Gallery.Treeview", background="#F1F2F6", foreground=self.text_dark, fieldbackground="#F1F2F6", font=("Segoe UI", 9))
        
        self.gallery_detail_tree = ttk.Treeview(
            tree_container, 
            selectmode="browse", 
            style="Gallery.Treeview",
            yscrollcommand=scroll_y.set
        )
        self.gallery_detail_tree.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=self.gallery_detail_tree.yview)
        
        self.gallery_detail_tree["columns"] = ("size", "offset", "date")
        self.gallery_detail_tree.column("#0", width=300, anchor="w")
        self.gallery_detail_tree.column("size", width=100, anchor="e")
        self.gallery_detail_tree.column("offset", width=120, anchor="e")
        self.gallery_detail_tree.column("date", width=150, anchor="center")
        
        self.gallery_detail_tree.heading("#0", text="İsim", anchor="w", command=lambda: self.sort_gallery_by_column("#0"))
        self.gallery_detail_tree.heading("size", text="Boyut", anchor="e", command=lambda: self.sort_gallery_by_column("size"))
        self.gallery_detail_tree.heading("offset", text="Disk Ofseti", anchor="e", command=lambda: self.sort_gallery_by_column("offset"))
        self.gallery_detail_tree.heading("date", text="Değiştirilme Tarihi", anchor="center", command=lambda: self.sort_gallery_by_column("date"))
        
        self.gallery_detail_tree.bind("<<TreeviewSelect>>", self.on_gallery_file_select)
        
        self.gallery_tree_item_map = {}
        self.on_gallery_search_change()

    def back_to_master_gallery(self):
        self.current_gallery_folder = None
        self.gallery_search_var.set("")
        self.stop_gallery_video_preview()
        self.reset_gallery_preview_panel()
        self.render_folder_gallery()

    def on_master_search_change(self):
        try:
            if self.current_gallery_folder is None:
                self.render_folder_gallery()
        except Exception as e:
            print(f"Master search change handling bypassed: {e}")

    def on_gallery_search_change(self):
        if not hasattr(self, "gallery_detail_tree") or not self.gallery_detail_tree:
            return
            
        try:
            if not self.gallery_detail_tree.winfo_exists():
                return
                
            self.gallery_detail_tree.delete(*self.gallery_detail_tree.get_children())
            self.gallery_tree_item_map.clear()
            
            folder_files = []
            for f in self.virtual_files:
                if f.get("custom_path"):
                    path_str = f["custom_path"]
                else:
                    path_str = f["category"]
                if path_str == self.current_gallery_folder:
                    folder_files.append(f)
                    
            query = self.gallery_search_var.get().lower().strip()
            filtered = [f for f in folder_files if query in f["name"].lower()]
            
            # Sort the filtered list based on selected column
            sort_col = getattr(self, "gallery_sort_column", None)
            sort_desc = getattr(self, "gallery_sort_descending", False)
            
            def natural_sort_key(s):
                import re
                return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]
                
            if sort_col == "#0":
                filtered.sort(key=lambda x: natural_sort_key(x["name"]), reverse=sort_desc)
            elif sort_col == "size":
                filtered.sort(key=lambda x: x["size"], reverse=sort_desc)
            elif sort_col == "offset":
                filtered.sort(key=lambda x: x["offset"], reverse=sort_desc)
            elif sort_col == "date":
                filtered.sort(key=lambda x: x.get("date", "-"), reverse=sort_desc)
            
            # Use batch insertion to prevent UI freezing on folders with many files
            batch_size = 100
            
            def insert_batch(start_idx):
                if not self.gallery_detail_tree.winfo_exists():
                    return
                # Check if search query has changed in the meantime (debounce check)
                if self.gallery_search_var.get().lower().strip() != query:
                    return
                    
                end_idx = min(start_idx + batch_size, len(filtered))
                for idx in range(start_idx, end_idx):
                    f = filtered[idx]
                    size_str = self.format_size(f["size"])
                    offset_mb = f["offset"] / (1024 * 1024)
                    node = self.gallery_detail_tree.insert(
                        "", "end",
                        text=f["name"],
                        values=(size_str, f"Ofset {f['offset']} ({offset_mb:.2f} MB)", f.get("date", "-"))
                    )
                    self.gallery_tree_item_map[node] = f
                    
                if end_idx < len(filtered):
                    self.after(5, lambda: insert_batch(end_idx))
                    
            insert_batch(0)
                
            if hasattr(self, "gallery_detail_lbl") and self.gallery_detail_lbl and self.gallery_detail_lbl.winfo_exists():
                self.gallery_detail_lbl.config(text=f"Klasör İçeriği: {self.current_gallery_folder} ({len(filtered)} / {len(folder_files)} dosya)")
        except Exception as e:
            print(f"Gallery search change handling bypassed: {e}")

    def sort_gallery_by_column(self, col):
        if not hasattr(self, "gallery_sort_column"):
            self.gallery_sort_column = None
        if not hasattr(self, "gallery_sort_descending"):
            self.gallery_sort_descending = False
            
        if self.gallery_sort_column == col:
            self.gallery_sort_descending = not self.gallery_sort_descending
        else:
            self.gallery_sort_column = col
            if col in ["size", "offset"]:
                self.gallery_sort_descending = True
            else:
                self.gallery_sort_descending = False
                
        # Update column headings with arrows
        cols_map = {
            "#0": "İsim",
            "size": "Boyut",
            "offset": "Disk Ofseti",
            "date": "Değiştirilme Tarihi"
        }
        for k, name in cols_map.items():
            arrow = ""
            if k == col:
                arrow = "  ▼" if self.gallery_sort_descending else "  ▲"
            self.gallery_detail_tree.heading(k, text=name + arrow)
            
        self.on_gallery_search_change()

    def on_gallery_file_select(self, event):
        selection = self.gallery_detail_tree.selection()
        if not selection:
            return
        node_id = selection[0]
        if node_id in self.gallery_tree_item_map:
            file_meta = self.gallery_tree_item_map[node_id]
            self.preview_selected_gallery_file(file_meta)

    def preview_selected_gallery_file(self, file_meta):
        self.current_gallery_preview_file_id = file_meta["id"]
        self.stop_gallery_video_preview()
        
        if file_meta["ext"].lower() == ".mp4":
            self.gallery_preview_canvas.pack_forget()
            self.gallery_preview_video_frame.pack(fill=tk.BOTH, expand=True)
            self.current_gallery_video_meta = file_meta
            
            size_str = self.format_size(file_meta["size"])
            self.gallery_vid_info_lbl.config(text=f"Dosya: {file_meta['name']}\nBoyut: {size_str}\nOfset: {file_meta['offset']}")
            self.gallery_vid_status_lbl.config(text="Önizleme hazırlanıyor...")
            self.gallery_preview_title.config(text=f"ÖNİZLEME: {file_meta['name'].upper()}")
            self.start_gallery_video_preview()
        else:
            self.gallery_preview_video_frame.pack_forget()
            self.gallery_preview_canvas.pack(fill=tk.BOTH, expand=True)
            self.current_gallery_video_meta = None
            
            self.gallery_preview_canvas.delete("all")
            self.gallery_preview_title.config(text=f"ÖNİZLEME: {file_meta['name'].upper()}")
            self.gallery_preview_canvas.create_text(20, 30, anchor="nw", fill=self.text_dark, text="Bellekten yükleniyor...", font=("Segoe UI", 10, "italic"))
            
            canvas_w = self.gallery_preview_canvas.winfo_width()
            canvas_h = self.gallery_preview_canvas.winfo_height()
            if canvas_w < 10: canvas_w = 320
            if canvas_h < 10: canvas_h = 350
            
            threading.Thread(target=self._async_load_gallery_preview, args=(file_meta, canvas_w, canvas_h), daemon=True).start()

    def _async_load_gallery_preview(self, file_meta, canvas_w, canvas_h):
        file_id = file_meta["id"]
        ext = file_meta["ext"].lower()
        preview_read_size = min(file_meta["size"], 5 * 1024 * 1024)
        
        try:
            # 1. Try to read from local exported/backup file if it exists
            local_path = self.get_file_exported_path(file_meta)
            raw_bytes = None
            if local_path and os.path.isfile(local_path):
                try:
                    with open(local_path, "rb") as lf:
                        raw_bytes = lf.read(preview_read_size)
                except:
                    pass
                    
            # 2. Fall back to raw disk read
            if raw_bytes is None:
                raw_bytes = self.read_raw_bytes(file_meta["offset"], preview_read_size)
                
            if ext in [".jpg", ".jpeg", ".png"] and HAS_PILLOW:
                from PIL import Image as PILImage
                img = PILImage.open(io.BytesIO(raw_bytes))
                img.thumbnail((canvas_w - 20, canvas_h - 20))
                img.load()
                
                self.msg_queue.put(("gallery_display_preview", {
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
                self.msg_queue.put(("gallery_display_preview", {
                    "file_id": file_id,
                    "type": "meta",
                    "text": meta_text,
                    "name": file_meta["name"]
                }))
        except Exception as e:
            err_msg = str(e)
            if "cannot identify image file" in err_msg:
                err_msg = "Görsel dosyası bozuk veya çözümlenemedi."
            self.msg_queue.put(("gallery_display_preview", {
                "file_id": file_id,
                "type": "error",
                "text": f"Önizleme yüklenemedi:\n{err_msg}",
                "name": file_meta["name"]
            }))

    def toggle_gallery_video_play_pause(self):
        self.toggle_video_play_pause()
        
    def toggle_gallery_video_mute(self):
        self.toggle_video_mute()

    def start_gallery_video_preview(self):
        if not self.current_gallery_video_meta:
            return
        self.gallery_vid_status_lbl.config(text="Diskten çıkartılıyor... Lütfen bekleyin.")
        self.gallery_vid_play_pause_btn.config(state="disabled")
        threading.Thread(target=self._async_extract_and_play_gallery_video, args=(self.current_gallery_video_meta,), daemon=True).start()

    def _async_extract_and_play_gallery_video(self, file_meta):
        temp_path = os.path.abspath("temp_gallery_video_preview.mp4")
        temp_audio_path = os.path.abspath("temp_gallery_video_preview.wav")
        try:
            # Clean up old previews
            for p in [temp_path, temp_audio_path]:
                if os.path.exists(p):
                    try: os.remove(p)
                    except: pass
            
            # Read first 20MB for fast preview
            preview_size = min(file_meta["size"], 20 * 1024 * 1024)
            video_bytes = self.read_raw_bytes(file_meta["offset"], preview_size)
            with open(temp_path, "wb") as f:
                f.write(video_bytes)
                
            self.msg_queue.put(("gallery_video_status", "Ses ayıklanıyor..."))
            
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
                
            self.msg_queue.put(("gallery_video_status", "Video yükleniyor..."))
            self.after(0, lambda: self.start_embedded_video_playback(
                temp_path, temp_audio_path, audio_extracted, self.gallery_vid_screen, self.gallery_vid_status_lbl,
                self.gallery_vid_timeline, self.gallery_vid_time_lbl, self.gallery_vid_play_pause_btn,
                self.gallery_vid_mute_btn, self.gallery_vid_volume_scale
            ))
        except Exception as e:
            self.msg_queue.put(("gallery_video_error", f"Video yüklenemedi: {e}"))

    def stop_gallery_video_preview(self):
        self.stop_embedded_video_playback()
        for p in ["temp_gallery_video_preview.mp4", "temp_gallery_video_preview.wav"]:
            temp_path = os.path.abspath(p)
            if os.path.exists(temp_path):
                try: os.remove(temp_path)
                except: pass

    def _async_load_card_thumbnails(self, request_map):
        import io
        from PIL import Image as PILImage, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        
        for path_str, file_list in request_map.items():
            for i, f in enumerate(file_list):
                ext = f["ext"].lower()
                if ext in [".jpg", ".jpeg", ".png"]:
                    try:
                        read_size = min(f["size"], 64 * 1024)
                        local_path = self.get_file_exported_path(f)
                        raw = None
                        if local_path and os.path.isfile(local_path):
                            try:
                                with open(local_path, "rb") as lf:
                                    raw = lf.read(read_size)
                            except:
                                pass
                        if raw is None:
                            raw = self.read_raw_bytes(f["offset"], read_size)
                        if ext in [".jpg", ".jpeg"] and hasattr(self, "repair_jpeg"):
                            raw = self.repair_jpeg(raw)
                        if raw:
                            img = PILImage.open(io.BytesIO(raw))
                            img.thumbnail((36, 36))
                            img.load()
                            self.msg_queue.put(("gallery_card_thumbnail", {
                                "key": f"card_{path_str}_{f['id']}",
                                "pil_image": img
                            }))
                    except:
                        pass

    def _async_load_detail_previews(self, previews):
        import io
        from PIL import Image as PILImage, ImageFile
        ImageFile.LOAD_TRUNCATED_IMAGES = True
        
        for f in previews:
            ext = f["ext"].lower()
            if ext in [".jpg", ".jpeg", ".png"]:
                try:
                    read_size = min(f["size"], 128 * 1024)
                    local_path = self.get_file_exported_path(f)
                    raw = None
                    if local_path and os.path.isfile(local_path):
                        try:
                            with open(local_path, "rb") as lf:
                                raw = lf.read(read_size)
                        except:
                            pass
                    if raw is None:
                        raw = self.read_raw_bytes(f["offset"], read_size)
                    if ext in [".jpg", ".jpeg"] and hasattr(self, "repair_jpeg"):
                        raw = self.repair_jpeg(raw)
                    if raw:
                        img = PILImage.open(io.BytesIO(raw))
                        img.thumbnail((100, 100))
                        img.load()
                        self.msg_queue.put(("gallery_detail_thumbnail", {
                            "file_id": f["id"],
                            "pil_image": img
                        }))
                except:
                    pass
