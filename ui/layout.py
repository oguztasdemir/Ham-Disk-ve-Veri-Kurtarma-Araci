import time
import tkinter as tk
from tkinter import ttk, messagebox
from config import CATEGORIES, APP_NAME

class LayoutMixin:
    def create_widgets(self):
        # Console Log Button is now placed in the sidebar to prevent visual overlap with the top status panel

        # Left Sidebar
        self.sidebar = tk.Frame(self, bg=self.sidebar_bg, width=260)
        self.sidebar.pack(side=tk.LEFT, fill=tk.Y)
        self.sidebar.pack_propagate(False)
        
        logo_lbl = tk.Label(self.sidebar, text=f"= {APP_NAME}", bg=self.sidebar_bg, fg=self.text_dark, font=("Segoe UI", 12, "bold"))
        logo_lbl.pack(anchor="w", padx=20, pady=20)
        
        self.dash_btn = tk.Button(self.sidebar, text="📊 Gösterge Tablosu", command=self.show_dashboard_view, bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=20, pady=10, font=("Segoe UI", 10, "bold"))
        self.dash_btn.pack(fill=tk.X)
 
        self.gallery_btn = tk.Button(self.sidebar, text="🖼️ Klasör Galeri Modu", command=self.show_folder_gallery_view, bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=20, pady=10, font=("Segoe UI", 10, "bold"))
        self.gallery_btn.pack(fill=tk.X)
 
        self.help_btn = tk.Button(self.sidebar, text="❓ Nasıl Çalışır / Yardım", command=self.show_help_window, bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=20, pady=10, font=("Segoe UI", 10, "bold"))
        self.help_btn.pack(fill=tk.X)
 
        self.log_btn = tk.Button(
            self.sidebar, 
            text="📋 Konsol Akışı", 
            command=self.show_console_log_window, 
            bg=self.sidebar_bg, 
            fg=self.text_dark, 
            activebackground="#E4E5EA", 
            activeforeground=self.text_dark, 
            borderwidth=0, 
            anchor="w", 
            padx=20, 
            pady=10, 
            font=("Segoe UI", 10, "bold")
        )
        self.log_btn.pack(fill=tk.X)
        
        tk.Label(self.sidebar, text="Sonuçlar", bg=self.sidebar_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.sidebar_buttons = {}
        self.all_files_btn = tk.Button(self.sidebar, text="📁 Tüm Dosyalar", command=lambda: self.set_category_filter("All"), bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=25, pady=8, font=("Segoe UI", 9))
        self.all_files_btn.pack(fill=tk.X)
        
        for cat_name, info in CATEGORIES.items():
            btn = tk.Button(self.sidebar, text=f"{info['icon']} {cat_name} (0)", command=lambda c=cat_name: self.set_category_filter(c), bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=25, pady=6, font=("Segoe UI", 9))
            btn.pack(fill=tk.X)
            self.sidebar_buttons[cat_name] = btn
            
        # Target Path selection at sidebar bottom
        sidebar_bottom = tk.Frame(self.sidebar, bg=self.sidebar_bg)
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=15)
        
        tk.Label(sidebar_bottom, text="Kurtarma Konumu:", bg=self.sidebar_bg, fg=self.text_gray, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.path_lbl = tk.Label(sidebar_bottom, text=self.selected_output_dir, bg="#E4E5EA", fg=self.text_dark, wraplength=220, justify="left", font=("Segoe UI", 8), padx=5, pady=5)
        self.path_lbl.pack(fill=tk.X, pady=5)
        
        change_path_btn = tk.Button(sidebar_bottom, text="Konumu Değiştir", command=self.select_output_directory, bg="#DCDDE1", fg=self.text_dark, borderwidth=0, pady=4, font=("Segoe UI", 8, "bold"))
        change_path_btn.pack(fill=tk.X)
        
        self.sidebar_change_backup_btn = tk.Button(
            sidebar_bottom, 
            text="💾 Yedek Değiştir", 
            command=lambda: self.show_backup_selector_flow(), 
            bg="#2ECC71", 
            fg=self.text_white, 
            borderwidth=0, 
            pady=6, 
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.sidebar_change_backup_btn.pack(fill=tk.X, pady=(10, 0))

        self.sidebar_change_session_btn = tk.Button(
            sidebar_bottom, 
            text="🔄 Oturumu Değiştir", 
            command=lambda: self.check_for_resume_state(force_show_dialog=True), 
            bg=self.accent_blue, 
            fg=self.text_white, 
            borderwidth=0, 
            pady=6, 
            font=("Segoe UI", 9, "bold"),
            cursor="hand2"
        )
        self.sidebar_change_session_btn.pack(fill=tk.X, pady=(10, 0))

        # Right Content Window
        self.content_frame = tk.Frame(self, bg=self.content_bg)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Real-time top status frame (now packed inside self.content_frame to prevent overlaps)
        self.top_status_frame = tk.Frame(self.content_frame, bg="#FFFFFF", highlightthickness=1, highlightbackground="#DCDDE1", bd=0, padx=12, pady=10)
        
        self.status_pills_frame = tk.Frame(self.top_status_frame, bg="#FFFFFF")
        self.status_pills_frame.pack(fill=tk.X, pady=(0, 6))
        
        self.top_current_scan_lbl = tk.Label(
            self.status_pills_frame, 
            text="Mevcut Tarama: %0.0 (0.00/0.00 GB) | - MB/s | Süre: 00:00 | Kalan: -", 
            bg="#E3F2FD", 
            fg="#0D47A1", 
            font=("Segoe UI", 9, "bold"), 
            padx=12, 
            pady=6,
            bd=0
        )
        self.top_current_scan_lbl.pack(side=tk.LEFT, padx=(0, 10))
        
        self.top_entire_disk_lbl = tk.Label(
            self.status_pills_frame, 
            text="Tüm Klasör: %0.0 (0.00/0.00 GB)", 
            bg="#E8F5E9", 
            fg="#1B5E20", 
            font=("Segoe UI", 9, "bold"), 
            padx=12, 
            pady=6,
            bd=0
        )
        self.top_entire_disk_lbl.pack(side=tk.LEFT)
        
        self.top_score_lbl = tk.Label(
            self.top_status_frame, 
            text="Tarama Kurtarma Skoru: %0 (Dosya Yok)", 
            bg="#FFF3E0", 
            fg="#E65100", 
            font=("Segoe UI", 9, "bold"), 
            padx=12, 
            pady=6,
            bd=0
        )
        self.top_score_lbl.pack(fill=tk.X)
        
        self.dashboard_view = tk.Frame(self.content_frame, bg=self.content_bg, padx=30, pady=20)
        self.file_view = tk.Frame(self.content_frame, bg=self.content_bg)
        
        self.init_dashboard_view()
        self.update_target_drive_status()
        self.init_file_view()
        self.show_dashboard_view()

    def init_dashboard_view(self):
        # Split dashboard into Left (Controls) and Right (RAM & Log Panel)
        # Pack fixed-width right frame first so it occupies its space, then left frame expands to fill remainder.
        self.dash_right_frame = tk.Frame(self.dashboard_view, bg=self.content_bg, width=280)
        self.dash_right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        self.dash_right_frame.pack_propagate(False)

        self.dash_left_frame = tk.Frame(self.dashboard_view, bg=self.content_bg)
        self.dash_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # System performance diagnostics panel has been relocated to the middle section to prevent overlaps.
        
        # Toggle Log Stream Button
        self.toggle_log_btn = tk.Button(
            self.dash_right_frame, 
            text="📖 Terminal Logunu Göster", 
            command=self.toggle_dashboard_log, 
            bg="#2F3542", 
            fg=self.text_white, 
            activebackground=self.accent_blue, 
            activeforeground=self.text_white, 
            borderwidth=0, 
            padx=10, 
            pady=5, 
            font=("Segoe UI", 8, "bold")
        )
        self.toggle_log_btn.pack(anchor="ne", fill=tk.X, pady=(0, 10))
        
        self.drive_info_frame = tk.LabelFrame(
            self.dash_right_frame, 
            text=" Sürücü S.M.A.R.T Sağlık Raporu ", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=10
        )
        self.drive_info_frame.pack(fill=tk.X, pady=(10, 0), side=tk.BOTTOM)
        
        self.lbl_drive_model = tk.Label(self.drive_info_frame, text="Model: Seçilmedi", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=230)
        self.lbl_drive_model.pack(fill=tk.X, pady=2)
        
        self.lbl_drive_health = tk.Label(self.drive_info_frame, text="Sağlık (SMART): -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.lbl_drive_health.pack(fill=tk.X, pady=2)
        
        self.lbl_drive_partition = tk.Label(self.drive_info_frame, text="Bölümleme Stili: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.lbl_drive_partition.pack(fill=tk.X, pady=2)
        
        self.lbl_drive_capacity = tk.Label(self.drive_info_frame, text="Kapasite: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.lbl_drive_capacity.pack(fill=tk.X, pady=2)

        self.lbl_drive_scanned = tk.Label(self.drive_info_frame, text="Taranan Alan: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold"), anchor="w")
        self.lbl_drive_scanned.pack(fill=tk.X, pady=2)

        # 💾 Recovery Target Drive Status Card
        self.target_drive_frame = tk.LabelFrame(
            self.dash_right_frame, 
            text=" 💾 Kurtarma Hedef Disk Durumu ", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=10
        )
        self.target_drive_frame.pack(fill=tk.X, pady=(10, 10), side=tk.BOTTOM)
        
        self.lbl_target_path = tk.Label(self.target_drive_frame, text="Konum: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w", justify="left", wraplength=230)
        self.lbl_target_path.pack(fill=tk.X, pady=2)
        
        self.lbl_target_total = tk.Label(self.target_drive_frame, text="Toplam Kapasite: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.lbl_target_total.pack(fill=tk.X, pady=2)
        
        self.lbl_target_used = tk.Label(self.target_drive_frame, text="Kullanılan / Boş: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.lbl_target_used.pack(fill=tk.X, pady=2)
        
        self.lbl_target_percent = tk.Label(self.target_drive_frame, text="Doluluk Oranı: -", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.lbl_target_percent.pack(fill=tk.X, pady=2)
        
        self.target_usage_bar = ttk.Progressbar(self.target_drive_frame, orient="horizontal", mode="determinate")
        self.target_usage_bar.pack(fill=tk.X, pady=(5, 2))
        
        # Embedded Log Panel (starts hidden)
        self.dash_log_panel = tk.Frame(self.dash_right_frame, bg="#1E1E24")
        
        log_scroll = ttk.Scrollbar(self.dash_log_panel, orient="vertical")
        log_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        self.dash_log_text = tk.Text(
            self.dash_log_panel, 
            bg="#2F3542", 
            fg="#FFFFFF", 
            insertbackground="white", 
            yscrollcommand=log_scroll.set, 
            font=("Consolas", 8), 
            state="disabled", 
            wrap="char"
        )
        self.dash_log_text.pack(fill=tk.BOTH, expand=True)
        log_scroll.config(command=self.dash_log_text.yview)
        
        self.dash_log_visible = False

        settings_bar = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        settings_bar.pack(fill=tk.X, pady=(0, 15))
        
        tk.Label(settings_bar, text="Kurtarılacak Diski Seçin:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(0, 6))
        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(settings_bar, textvariable=self.drive_var, state="readonly", width=25)
        self.drive_combo.pack(side=tk.LEFT, padx=(0, 6))
        self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_select)
        
        refresh_btn = tk.Button(settings_bar, text="Yenile", command=self.load_physical_drives, bg="#F1F2F6", fg=self.text_dark, borderwidth=1, relief="solid", padx=8, pady=3, font=("Segoe UI", 8, "bold"))
        refresh_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        self.dash_path_btn = tk.Button(settings_bar, text="Taşınacak Yeri Seçin", command=self.select_output_directory, bg="#F1F2F6", fg=self.text_dark, borderwidth=1, relief="solid", font=("Segoe UI", 8, "bold"), padx=10, pady=3, cursor="hand2")
        self.dash_path_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.start_btn = tk.Button(settings_bar, text="⚡ KLASÖR YAPISINI VE DOSYALARI TARA", command=self.show_scan_progress_modal, bg=self.accent_blue, fg=self.text_white, borderwidth=0, padx=12, pady=4, font=("Segoe UI", 9, "bold"), cursor="hand2")
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.close_session_btn = tk.Button(
            settings_bar, 
            text="Oturumu Kapat", 
            command=self.close_current_session, 
            bg="#FF4757", 
            fg=self.text_white, 
            borderwidth=0, 
            padx=10, 
            pady=4, 
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        )
        
        self.dash_show_adv_var = tk.BooleanVar(value=False)
        self.dash_adv_btn = tk.Checkbutton(
            settings_bar, 
            text="⚙️ Gelişmiş Ayarlar", 
            variable=self.dash_show_adv_var, 
            command=self.toggle_dash_adv_panel, 
            bg=self.content_bg, 
            fg=self.accent_blue, 
            activebackground=self.content_bg, 
            activeforeground=self.accent_blue,
            font=("Segoe UI", 8, "bold")
        )
        self.dash_adv_btn.pack(side=tk.RIGHT, padx=(10, 0))
        
        # Parallel scan settings bar (not packed initially)
        self.parallel_bar = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        
        self.parallel_cb = tk.Checkbutton(
            self.parallel_bar,
            text="Paralel Motorlar ile Parçalı Tara",
            variable=self.use_parallel_var,
            command=self.toggle_parallel_options,
            bg=self.content_bg,
            fg=self.accent_blue,
            activebackground=self.content_bg,
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.parallel_cb.pack(side=tk.LEFT, padx=(0, 15))
        
        self.worker_lbl = tk.Label(self.parallel_bar, text="Motor Sayısı (Thread):", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.worker_lbl.pack(side=tk.LEFT, padx=(0, 5))
        
        self.worker_combo = ttk.Combobox(
            self.parallel_bar,
            textvariable=self.worker_count_var,
            values=[str(i) for i in range(1, 17)],
            state="disabled",
            width=5
        )
        self.worker_combo.pack(side=tk.LEFT, padx=(0, 15))
        
        self.segment_lbl = tk.Label(self.parallel_bar, text="Parça Boyutu (GB):", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.segment_lbl.pack(side=tk.LEFT, padx=(0, 5))
        
        self.segment_entry = tk.Entry(
            self.parallel_bar,
            textvariable=self.segment_size_gb_var,
            state="disabled",
            width=8
        )
        self.segment_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        self.parallel_warn_lbl = tk.Label(
            self.parallel_bar,
            text="⚠️ HDD sürücüler için 1 veya 2 motor önerilir!",
            bg=self.content_bg,
            fg="#FF4757",
            font=("Segoe UI", 8, "italic")
        )
        self.parallel_warn_lbl.pack(side=tk.LEFT)
        
        # Custom range settings bar (not packed initially)
        self.custom_range_bar = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        
        self.custom_range_cb = tk.Checkbutton(
            self.custom_range_bar,
            text="Özel Bellek Aralığı Tara",
            variable=self.use_custom_range_var,
            command=self.toggle_parallel_options,
            bg=self.content_bg,
            fg=self.accent_blue,
            activebackground=self.content_bg,
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.custom_range_cb.pack(side=tk.LEFT, padx=(0, 15))

        
        self.scan_from_end_cb = tk.Checkbutton(
            self.custom_range_bar,
            text="Sondan Ara",
            variable=self.scan_from_end_var,
            bg=self.content_bg,
            fg=self.accent_blue,
            activebackground=self.content_bg,
            activeforeground=self.accent_blue,
            font=("Segoe UI", 9, "bold")
        )
        self.scan_from_end_cb.pack(side=tk.LEFT, padx=(15, 0))
        
        self.custom_block_lbl = tk.Label(self.custom_range_bar, text="Blok Aralığı (1-100):", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold"))
        self.custom_block_lbl.pack(side=tk.LEFT, padx=(10, 5))
        
        self.custom_block_entry = tk.Entry(
            self.custom_range_bar,
            textvariable=self.custom_block_range_var,
            state="disabled",
            width=10,
            font=("Segoe UI", 9, "bold")
        )
        self.custom_block_entry.pack(side=tk.LEFT, padx=(0, 10))
        
        # Category Selection Bar (not packed initially)
        self.category_select_bar = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        
        tk.Label(
            self.category_select_bar, 
            text="Taranacak Dosya Türleri:", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 9, "bold")
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        self.category_checkboxes = []
        for name, info in CATEGORIES.items():
            cb = tk.Checkbutton(
                self.category_select_bar,
                text=f"{info['icon']} {name}",
                variable=self.category_vars[name],
                command=self.save_app_settings,
                bg=self.content_bg,
                fg=info['color'],
                activebackground=self.content_bg,
                activeforeground=info['color'],
                font=("Segoe UI", 9, "bold")
            )
            cb.pack(side=tk.LEFT, padx=(0, 15))
            self.category_checkboxes.append(cb)
            
        self.scan_header_lbl = tk.Label(self.dash_left_frame, text="Cihaz Seçin ve Klasör Yapısını Tarayın", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 16, "bold"))
        self.scan_header_lbl.pack(anchor="w", pady=(0, 5))
        
        self.scan_progress_lbl = tk.Label(self.dash_left_frame, text="Taramayı başlattığınızda veriler yer kaplamadan burada listelenecektir.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 10))
        self.scan_progress_lbl.pack(anchor="w", pady=(0, 10))
        
        # Grid of 6 category cards on the left, system stats on the right
        self.cards_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.cards_frame.pack(fill=tk.X, pady=4)
        
        # Left subframe for cards
        cards_left_subframe = tk.Frame(self.cards_frame, bg=self.content_bg)
        cards_left_subframe.pack(side=tk.LEFT)
        
        self.card_widgets = {}
        categories_list = list(CATEGORIES.keys())
        for idx, name in enumerate(categories_list):
            info = CATEGORIES[name]
            r = idx // 3
            c = idx % 3
            
            card = tk.Frame(cards_left_subframe, bg=info["color"], width=180, height=90, bd=0, padx=10, pady=8)
            card.grid(row=r, column=c, padx=4, pady=4)
            card.grid_propagate(False)
            
            icon_lbl = tk.Label(card, text=info["icon"], bg=info["color"], fg=self.text_white, font=("Segoe UI", 16))
            icon_lbl.pack(anchor="nw")
            
            title_lbl = tk.Label(card, text=name, bg=info["color"], fg=self.text_white, font=("Segoe UI", 9, "bold"))
            title_lbl.pack(anchor="sw", pady=(4, 0))
            
            count_lbl = tk.Label(card, text="0 Dosya Bulundu", bg=info["color"], fg=self.text_white, font=("Segoe UI", 8))
            count_lbl.pack(anchor="sw")
            
            # Make the entire card interactive and clickable
            for widget in (card, icon_lbl, title_lbl, count_lbl):
                widget.bind("<Button-1>", lambda event, cat_name=name: self.set_category_filter(cat_name))
                widget.config(cursor="hand2")
                
            self.card_widgets[name] = {"count_lbl": count_lbl, "frame": card}
            
        # Right subframe for system performance info
        sys_status_frame = tk.LabelFrame(
            self.cards_frame, 
            text=" Sistem Performansı & Aygıtlar ", 
            bg=self.content_bg, 
            fg=self.text_dark, 
            font=("Segoe UI", 9, "bold"),
            padx=10,
            pady=8
        )
        sys_status_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(15, 10), pady=4)
        
        self.ram_lbl = tk.Label(sys_status_frame, text="RAM: Yükleniyor...", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.ram_lbl.pack(fill=tk.X, pady=2)
        
        self.cpu_lbl = tk.Label(sys_status_frame, text="CPU Yükü: Yükleniyor...", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.cpu_lbl.pack(fill=tk.X, pady=2)
        
        self.gpu_lbl = tk.Label(sys_status_frame, text="GPU Yükü: Yükleniyor...", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.gpu_lbl.pack(fill=tk.X, pady=2)
        
        self.temp_lbl = tk.Label(sys_status_frame, text="CPU Sıcaklığı: Yükleniyor...", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9), anchor="w")
        self.temp_lbl.pack(fill=tk.X, pady=2)
        
        self.engine_lbl = tk.Label(sys_status_frame, text="Aktif Motor: CPU (En Optimize Hız)", bg=self.content_bg, fg="#2ECC71", font=("Segoe UI", 9, "bold"), anchor="w")
        self.engine_lbl.pack(fill=tk.X, pady=2)
        
        self.gpu_acc_lbl = tk.Label(sys_status_frame, text="GPU Hızlandırma: Aktif (Arayüz & Çizim)", bg=self.content_bg, fg=self.accent_blue, font=("Segoe UI", 9, "bold"), anchor="w")
        self.gpu_acc_lbl.pack(fill=tk.X, pady=2)
            
        # Disk Visual Map Frame
        self.disk_map_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.disk_map_frame.pack(fill=tk.X, pady=(5, 0))
        
        map_title_row = tk.Frame(self.disk_map_frame, bg=self.content_bg)
        map_title_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(map_title_row, text="Diskin Görsel Durum Haritası (Detaylar için tıklayın)", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
        # Legend (Lejant)
        legend_frame = tk.Frame(map_title_row, bg=self.content_bg)
        legend_frame.pack(side=tk.RIGHT)
        
        # Unscanned legend
        tk.Frame(legend_frame, bg="#2F3542", width=12, height=12).pack(side=tk.LEFT, padx=(10, 4))
        tk.Label(legend_frame, text="Taranmadı", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        
        # Scanning legend
        tk.Frame(legend_frame, bg="#FF9F43", width=12, height=12).pack(side=tk.LEFT, padx=(10, 4))
        tk.Label(legend_frame, text="Taranıyor", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        
        # Scanned legend
        tk.Frame(legend_frame, bg="#10AC84", width=12, height=12).pack(side=tk.LEFT, padx=(10, 4))
        tk.Label(legend_frame, text="Tarandı", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8)).pack(side=tk.LEFT)
        
        self.disk_map_canvas = tk.Canvas(self.disk_map_frame, bg="#1E272E", height=36, highlightthickness=1, highlightbackground="#57606F", cursor="hand2")
        self.disk_map_canvas.pack(fill=tk.X)
        self.disk_map_canvas.bind("<Motion>", self.on_disk_map_hover)
        self.disk_map_canvas.bind("<Leave>", self.on_disk_map_leave)
        self.disk_map_canvas.bind("<Button-1>", self.on_disk_map_double_click)
            
        ctrl_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        ctrl_frame.pack(fill=tk.X, pady=8)
        
        self.pause_btn = tk.Button(ctrl_frame, text="DURAKLAT", command=self.pause_recovery, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, padx=12, pady=4, font=("Segoe UI", 8, "bold"))
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 6))
        
        self.resume_btn = tk.Button(ctrl_frame, text="DEVAM ET", command=self.resume_recovery, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, padx=12, pady=4, font=("Segoe UI", 8, "bold"))
        self.resume_btn.pack(side=tk.LEFT, padx=(0, 6))
        self.backup_btn = tk.Button(ctrl_frame, text="💾 YEDEK AL", command=self.manual_backup, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, padx=12, pady=4, font=("Segoe UI", 8, "bold"))
        self.backup_btn.pack(side=tk.LEFT, padx=(0, 6))

        self.bar_detail_btn = tk.Button(
            ctrl_frame, 
            text="🔍 Bar Detayına Git / Kuyruk Yönetimi", 
            command=lambda: self.on_disk_map_double_click(None), 
            bg=self.accent_blue, 
            fg=self.text_white, 
            borderwidth=0, 
            padx=12, 
            pady=4, 
            font=("Segoe UI", 8, "bold"),
            cursor="hand2"
        )
        self.bar_detail_btn.pack(side=tk.RIGHT, padx=(6, 0))
        
        self.inspect_btn = tk.Button(ctrl_frame, text="🔎 Bulunan Öğeleri İnceleyin", command=self.show_file_view, bg=self.accent_blue, fg=self.text_white, borderwidth=0, padx=14, pady=4, font=("Segoe UI", 8, "bold"), cursor="hand2")
        self.inspect_btn.pack(side=tk.RIGHT, padx=(6, 0))
        
        self.status_lbl = tk.Label(self.dash_left_frame, text="Hazır.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9))
        self.status_lbl.pack(side=tk.BOTTOM, anchor="w", pady=(10, 0))
 
        # Dedicated Progress & Stats Frame at the bottom
        self.bottom_progress_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.bottom_progress_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
        
        # Split into left and right subframes to prevent vertical crowding
        prog_left_col = tk.Frame(self.bottom_progress_frame, bg=self.content_bg)
        prog_left_col.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 15))
        
        prog_right_col = tk.Frame(self.bottom_progress_frame, bg=self.content_bg)
        prog_right_col.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(15, 0))
        
        # --- LEFT COLUMN (Current Scan Progress & Stats) ---
        self.lbl_progress_title = tk.Label(prog_left_col, text="Mevcut Tarama İlerlemesi:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_progress_title.pack(anchor="w")
        self.lbl_progress_val = tk.Label(prog_left_col, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.lbl_progress_val.pack(anchor="w", pady=(2, 4))
        
        self.progress_bar = ttk.Progressbar(prog_left_col, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, pady=(2, 8))
        
        # Stats Frame under the current scan progress bar
        self.stats_frame = tk.Frame(prog_left_col, bg=self.content_bg)
        self.stats_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.lbl_speed_title = tk.Label(self.stats_frame, text="Tarama Hızı:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8, "bold"))
        self.lbl_speed_title.grid(row=0, column=0, sticky="w", padx=(0, 5), pady=2)
        self.lbl_speed_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 8))
        self.lbl_speed_val.grid(row=0, column=1, sticky="w", padx=(0, 15), pady=2)
        
        self.lbl_elapsed_title = tk.Label(self.stats_frame, text="Geçen Süre:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8, "bold"))
        self.lbl_elapsed_title.grid(row=0, column=2, sticky="w", padx=(0, 5), pady=2)
        self.lbl_elapsed_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 8))
        self.lbl_elapsed_val.grid(row=0, column=3, sticky="w", padx=(0, 15), pady=2)
        
        self.lbl_eta_title = tk.Label(self.stats_frame, text="Kalan Süre:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8, "bold"))
        self.lbl_eta_title.grid(row=0, column=4, sticky="w", padx=(0, 5), pady=2)
        self.lbl_eta_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 8))
        self.lbl_eta_val.grid(row=0, column=5, sticky="w", pady=2)
        
        # --- RIGHT COLUMN (Entire Disk Progress & Backup/Export Progress) ---
        self.lbl_entire_progress_title = tk.Label(prog_right_col, text="Tüm Disk İlerlemesi:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_entire_progress_title.pack(anchor="w")
        self.lbl_entire_progress_val = tk.Label(prog_right_col, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.lbl_entire_progress_val.pack(anchor="w", pady=(2, 4))
        
        self.entire_progress_bar = ttk.Progressbar(prog_right_col, orient="horizontal", mode="determinate")
        self.entire_progress_bar.pack(fill=tk.X, pady=(2, 8))
        
        self.lbl_backup_progress_title = tk.Label(prog_right_col, text="Yedekleme / Aktarım İlerlemesi:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_backup_progress_title.pack(anchor="w")
        self.lbl_backup_progress_val = tk.Label(prog_right_col, text="Beklemede (Aktif yedekleme yok)", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 8))
        self.lbl_backup_progress_val.pack(anchor="w", pady=(2, 4))
        
        self.backup_progress_bar = ttk.Progressbar(prog_right_col, orient="horizontal", mode="determinate")
        self.backup_progress_bar.pack(fill=tk.X, pady=(2, 0))

    def init_file_view(self):
        top_bar = tk.Frame(self.file_view, bg=self.content_bg, padx=15, pady=10, bd=1, relief="solid")
        top_bar.pack(fill=tk.X)
        
        back_btn = tk.Button(top_bar, text="◀ Gösterge Tablosuna Dön", command=self.show_dashboard_view, bg="#F1F2F6", fg=self.text_dark, borderwidth=0, padx=10, pady=5, font=("Segoe UI", 9, "bold"))
        back_btn.pack(side=tk.LEFT)
        
        title_frame = tk.Frame(top_bar, bg=self.content_bg)
        title_frame.pack(side=tk.LEFT, padx=20)
        
        self.view_title = tk.Label(title_frame, text="Sürücü Seçilmedi", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 14, "bold"))
        self.view_title.pack(anchor="w")
        
        self.view_subtitle = tk.Label(title_frame, text="0 dosya / 0.00 GB", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9))
        self.view_subtitle.pack(anchor="w")
        
        help_btn = tk.Button(top_bar, text="[Klasör Yapısı Hakkında Bilgi]", command=self.show_folder_info, bg=self.content_bg, fg=self.accent_blue, activebackground=self.content_bg, activeforeground=self.accent_blue, borderwidth=0, font=("Segoe UI", 9, "underline", "bold"), cursor="hand2")
        help_btn.pack(side=tk.RIGHT)

        pane = tk.PanedWindow(self.file_view, orient=tk.HORIZONTAL, bg="#E4E5EA", sashwidth=4)
        pane.pack(fill=tk.BOTH, expand=True)
        
        list_panel = tk.Frame(pane, bg=self.content_bg, padx=15, pady=15)
        pane.add(list_panel, minsize=450)
        
        filter_row = tk.Frame(list_panel, bg=self.content_bg)
        filter_row.pack(fill=tk.X, pady=(0, 10))
        
        hide_cb = tk.Checkbutton(filter_row, text="Yalnızca Önizlenebilir Olanları Göster", variable=self.hide_non_previewable, command=self.update_file_listbox_view, bg=self.content_bg, fg=self.accent_blue, activebackground=self.content_bg, activeforeground=self.accent_blue, font=("Segoe UI", 9, "bold"))
        hide_cb.pack(side=tk.LEFT)
        
        tk.Label(filter_row, text="Sıralama:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9)).pack(side=tk.LEFT, padx=(15, 5))
        self.sort_combo = ttk.Combobox(filter_row, textvariable=self.sort_var, values=[
            "Varsayılan (Bulunma Sırası)", 
            "İsim (A-Z)", 
            "İsim (Z-A)", 
            "Boyut (Büyükten Küçüğe)", 
            "Boyut (Küçükten Büyüye)"
        ], state="readonly", width=18)
        self.sort_combo.pack(side=tk.LEFT)
        self.sort_combo.bind("<<ComboboxSelected>>", lambda e: self.on_sort_combo_change())
        
        tk.Label(filter_row, text="🔍 Ara:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(15, 5))
        self.search_var = tk.StringVar()
        self.search_entry = tk.Entry(filter_row, textvariable=self.search_var, width=15)
        self.search_entry.pack(side=tk.LEFT, padx=(0, 5))
        self.search_entry.bind("<KeyRelease>", lambda e: self.update_file_listbox_view())
        
        # Create a frame to hold Treeview and Scrollbars
        tree_frame = tk.Frame(list_panel, bg=self.content_bg)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # Scrollbars
        tree_scroll_y = ttk.Scrollbar(tree_frame, orient="vertical")
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = ttk.Scrollbar(tree_frame, orient="horizontal")
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Style configuration for a clean modern Treeview
        style = ttk.Style()
        style.configure("Custom.Treeview", background="#F1F2F6", foreground=self.text_dark, fieldbackground="#F1F2F6", font=("Segoe UI", 9))
        style.map("Custom.Treeview", background=[("selected", self.accent_blue)], foreground=[("selected", self.text_white)])
        
        self.file_tree = ttk.Treeview(
            tree_frame, 
            selectmode="extended", 
            style="Custom.Treeview",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set
        )
        self.file_tree.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y.config(command=self.file_tree.yview)
        tree_scroll_x.config(command=self.file_tree.xview)
        
        self.file_tree["columns"] = ("chance", "date", "preview", "type", "size", "offset")
        self.file_tree.column("#0", width=220, minwidth=150, anchor="w")
        self.file_tree.column("chance", width=120, minwidth=80, anchor="center")
        self.file_tree.column("date", width=120, minwidth=80, anchor="center")
        self.file_tree.column("preview", width=100, minwidth=80, anchor="center")
        self.file_tree.column("type", width=90, minwidth=70, anchor="center")
        self.file_tree.column("size", width=80, minwidth=60, anchor="e")
        self.file_tree.column("offset", width=110, minwidth=80, anchor="e")
        
        self.file_tree.heading("#0", text="İsim", anchor="w", command=lambda: self.sort_by_column("#0"))
        self.file_tree.heading("chance", text="Kurtarma İhtimali", anchor="center", command=lambda: self.sort_by_column("chance"))
        self.file_tree.heading("date", text="Değiştirilme Tarihi", anchor="center", command=lambda: self.sort_by_column("date"))
        self.file_tree.heading("preview", text="Önizleme", anchor="center", command=lambda: self.sort_by_column("preview"))
        self.file_tree.heading("type", text="Tür", anchor="center", command=lambda: self.sort_by_column("type"))
        self.file_tree.heading("size", text="Boyut", anchor="e", command=lambda: self.sort_by_column("size"))
        self.file_tree.heading("offset", text="Disk Ofseti", anchor="e", command=lambda: self.sort_by_column("offset"))
        
        self.file_tree.bind("<<TreeviewSelect>>", self.on_file_select)
        
        btn_frame = tk.Frame(list_panel, bg=self.content_bg)
        btn_frame.pack(fill=tk.X)
        
        self.move_to_folder_btn = tk.Button(btn_frame, text="📁 Seçilenleri Klasöre Taşı", command=self.move_selected_to_folder, bg="#2F3542", fg=self.text_white, borderwidth=0, padx=15, pady=8, font=("Segoe UI", 9, "bold"))
        self.move_to_folder_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 5))
        
        self.export_sel_btn = tk.Button(btn_frame, text="Seçilenleri Bilgisayara Kaydet", command=self.export_selected, bg=self.accent_blue, fg=self.text_white, borderwidth=0, padx=15, pady=8, font=("Segoe UI", 9, "bold"))
        self.export_sel_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 5))
        
        self.export_all_btn = tk.Button(btn_frame, text="Hepsini Klasörlere Bölerek Kaydet", command=self.export_all, bg="#2F3542", fg=self.text_white, borderwidth=0, padx=15, pady=8, font=("Segoe UI", 9, "bold"))
        self.export_all_btn.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(5, 0))
        
        preview_panel = tk.Frame(pane, bg=self.content_bg, padx=15, pady=15)
        pane.add(preview_panel, minsize=320)
        
        self.preview_title = tk.Label(preview_panel, text="BELLEK ÖNİZLEME", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 11, "bold"))
        self.preview_title.pack(anchor="w", pady=(0, 8))
        
        self.preview_canvas = tk.Canvas(preview_panel, bg="#F1F2F6", highlightthickness=1, highlightbackground="#DCDDE1")
        self.preview_canvas.pack(fill=tk.BOTH, expand=True)
        
        # Video Preview Panel
        self.preview_video_frame = tk.Frame(preview_panel, bg="#F1F2F6", bd=1, relief="solid", padx=15, pady=20)
        
        vid_container = tk.Frame(self.preview_video_frame, bg="#F1F2F6")
        vid_container.pack(fill=tk.BOTH, expand=True)
        
        vid_screen_container = tk.Frame(vid_container, width=280, height=200, bg="#000000")
        vid_screen_container.pack_propagate(False)
        vid_screen_container.pack(pady=10)
        
        self.vid_screen = tk.Label(vid_screen_container, bg="#000000", fg=self.accent_blue, text="📺 Video Hazır", font=("Segoe UI", 16, "bold"), cursor="hand2")
        self.vid_screen.pack(fill=tk.BOTH, expand=True)
        
        self.vid_info_lbl = tk.Label(vid_container, text="Video Yükleniyor...", bg="#F1F2F6", fg=self.text_dark, font=("Segoe UI", 9, "bold"), justify="center", wraplength=260)
        self.vid_info_lbl.pack(pady=5)
        
        self.vid_timeline = tk.Scale(vid_container, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False, bg="#F1F2F6", highlightthickness=0, bd=0, sliderlength=15, width=10, cursor="sb_h_double_arrow")
        self.vid_timeline.pack(fill=tk.X, padx=5, pady=2)
        
        self.vid_time_lbl = tk.Label(vid_container, text="00:00 / 00:00", bg="#F1F2F6", fg=self.text_dark, font=("Segoe UI", 9, "bold"))
        self.vid_time_lbl.pack(pady=2)
        
        controls_frame = tk.Frame(vid_container, bg="#F1F2F6")
        controls_frame.pack(pady=5)
        
        self.vid_play_pause_btn = tk.Button(controls_frame, text="▶", command=self.toggle_video_play_pause, bg=self.accent_blue, fg=self.text_white, font=("Segoe UI", 10, "bold"), width=3, borderwidth=0, cursor="hand2")
        self.vid_play_pause_btn.pack(side=tk.LEFT, padx=2)
        
        self.vid_stop_btn = tk.Button(controls_frame, text="⏹", command=self.stop_video_preview, bg="#FF4757", fg=self.text_white, font=("Segoe UI", 10, "bold"), width=3, borderwidth=0, cursor="hand2")
        self.vid_stop_btn.pack(side=tk.LEFT, padx=2)
        
        self.vid_mute_btn = tk.Button(controls_frame, text="🔊", command=self.toggle_video_mute, bg="#CED6E0", fg=self.text_dark, font=("Segoe UI", 10, "bold"), width=3, borderwidth=0, cursor="hand2")
        self.vid_mute_btn.pack(side=tk.LEFT, padx=(10, 2))
        
        self.vid_volume_scale = tk.Scale(controls_frame, from_=0, to=100, orient=tk.HORIZONTAL, showvalue=False, bg="#F1F2F6", highlightthickness=0, bd=0, sliderlength=12, width=8, length=70, cursor="hand2")
        self.vid_volume_scale.set(70)
        self.vid_volume_scale.pack(side=tk.LEFT, padx=2)
        
        self.vid_status_lbl = tk.Label(vid_container, text="Oynatmaya hazır.", bg="#F1F2F6", fg=self.text_gray, font=("Segoe UI", 9, "italic"))
        self.vid_status_lbl.pack(pady=5)
        
        self.current_video_meta = None

    def show_dashboard_view(self):
        self.file_view.pack_forget()
        if hasattr(self, "folder_gallery_view") and self.folder_gallery_view:
            self.folder_gallery_view.pack_forget()
        self.dashboard_view.pack(fill=tk.BOTH, expand=True)
        self.draw_disk_map()
        if hasattr(self, "log_btn"):
            self.log_btn.lift()
        if hasattr(self, "top_status_frame") and self.top_status_frame.winfo_manager():
            self.top_status_frame.lift()

    def show_file_view(self):
        self.dashboard_view.pack_forget()
        if hasattr(self, "folder_gallery_view") and self.folder_gallery_view:
            self.folder_gallery_view.pack_forget()
        self.file_view.pack(fill=tk.BOTH, expand=True)
        if hasattr(self, "log_btn"):
            self.log_btn.lift()
        if hasattr(self, "top_status_frame") and self.top_status_frame.winfo_manager():
            self.top_status_frame.lift()
        
        # Update details header title/subtitle dynamically
        total_files = len(self.virtual_files)
        total_bytes = sum(f["size"] for f in self.virtual_files)
        
        selected_disp = self.drive_var.get()
        drive_name = selected_disp.split(":")[1].strip() if ":" in selected_disp else (selected_disp if selected_disp else "Sanal Disk")
        
        self.view_title.config(text=drive_name)
        self.view_subtitle.config(text=f"{total_files} dosya / {self.format_size(total_bytes)}")
        
        self.update_file_listbox_view()

    def set_category_filter(self, category):
        self.selected_category_filter = category
        if category == "All":
            self.view_title.config(text="TÜM BULUNAN DOSYALAR")
        else:
            self.view_title.config(text=f"BULUNAN DOSYALAR -> {category.upper()}")
        self.show_file_view()

    def show_folder_info(self):
        from tkinter import messagebox
        info_text = (
            "Orijinal Klasör Yapısı Neden Kurtarılamıyor?\n\n"
            "Xbox, harici diski biçimlendirirken 'Hızlı Biçimlendirme' yapmıştır. Hızlı biçimlendirme dosya sisteminin ana "
            "indeks tablolarını (NTFS'teki MFT veya FAT tablosu gibi) siler.\n\n"
            "Bu program, diski ham sektör düzeyinde tarayan 'File Carving' yöntemini kullanır. Bu yöntem dosyaların nerede başlayıp "
            "nerede bittiğini dosya imzalarından (header/footer) tespit ederek doğrudan kurtarır. Ancak orijinal klasör yolları ve dosya adları "
            "indeks tablolarıyla birlikte silindiği için ham taramada klasör yapısı kurtarılamaz.\n\n"
            "İpucu: Orijinal klasör yapısı ve dosya adlarını geri getirmeyi denemek için, silinen indeks tablolarının kırıntılarını "
            "tarayabilen ticari derin tarama yazılımlarını (Recuva, EaseUS Data Recovery Wizard veya Disk Drill gibi) kullanabilirsiniz."
        )
        messagebox.showinfo("Orijinal Klasör Yapısı Hakkında", info_text)

    def show_help_window(self):
        help_win = tk.Toplevel(self)
        help_win.title("Nasıl Çalışır & Bilgi Kılavuzu")
        help_win.geometry("800x600")
        help_win.configure(bg="#1E1E24")
        help_win.transient(self)
        
        # A beautiful header
        header_frame = tk.Frame(help_win, bg="#0084FF", pady=15)
        header_frame.pack(fill=tk.X)
        
        title_lbl = tk.Label(header_frame, text=f"🛠️ {APP_NAME} - Profesyonel Veri Kurtarma Kılavuzu", bg="#0084FF", fg="#FFFFFF", font=("Segoe UI", 14, "bold"))
        title_lbl.pack()
        
        subtitle_lbl = tk.Label(header_frame, text="Uygulama Çalışma Mantığı ve Gelişmiş Algoritmalar", bg="#0084FF", fg="#E4E5EA", font=("Segoe UI", 9, "italic"))
        subtitle_lbl.pack()
        
        # Notebook for tabbed guide
        notebook = ttk.Notebook(help_win)
        notebook.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Styling Notebook
        style = ttk.Style()
        style.configure("TNotebook", background="#1E1E24", borderwidth=0)
        style.configure("TNotebook.Tab", background="#2F3542", foreground="#2F3542", font=("Segoe UI", 9, "bold"), padding=[15, 5])
        
        # Tab 1: File Carving
        tab1 = tk.Frame(notebook, bg="#FFFFFF", padx=20, pady=20)
        notebook.add(tab1, text="Dosya Oymacılığı (Carving)")
        
        t1_text = (
            "📌 File Carving (Dosya Oymacılığı) Nedir?\n\n"
            "Diskiniz hızlı biçimlendirildiğinde veya dosya sistemi (MFT, FAT) çöktüğünde, işletim sistemi dosyaların konumlarını ve isimlerini bulamaz. "
            "Ancak verinin kendisi disk üzerinde fiziksel olarak durmaya devam eder.\n\n"
            "File Carving yöntemi, disk üzerindeki her sektörü sırayla tarar ve dosyalara ait bilinen 'Magic Bytes' (imza) yapılarını arar:\n"
            "  • JPEG resimleri: FF D8 FF ile başlar, FF D9 ile biter.\n"
            "  • PNG resimleri: 89 50 4E 47 ile başlar.\n"
            "  • PDF belgeleri: %PDF- ile başlar, %%EOF ile biter.\n\n"
            "Program bu imzaları bulduğunda veriyi ham sektörlerden kopyalar ve yeni bir dosya olarak kurtarır."
        )
        tk.Label(tab1, text=t1_text, bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=720).pack(fill=tk.BOTH, expand=True)
        
        # Tab 2: Neden Klasör İsimleri Yok
        tab2 = tk.Frame(notebook, bg="#FFFFFF", padx=20, pady=20)
        notebook.add(tab2, text="Klasör Yapıları & İsimler")
        
        t2_text = (
            "📌 Klasör İsimleri ve Orijinal Klasör Yapısı Neden Kurtarılamaz?\n\n"
            "Dosya adları, oluşturulma tarihleri ve klasör hiyerarşisi diskteki indeks tablolarında (örneğin NTFS'teki MFT - Master File Table) tutulur.\n\n"
            "Eğer disk biçimlendirilmişse bu tablolar temizlenmiştir. Dosya Oymacılığı sadece ham veriyi kurtarabilir. Bu yüzden dosyaların adları 'kurtarilan_resim_1.jpg' gibi otomatik üretilir.\n\n"
            f"💡 {APP_NAME} Çözümü (Sanal Klasörleme):\n"
            "Bu eksikliği gidermek için programda 'Sanal Klasörleme' sistemi mevcuttur. Kurtarmak istediğiniz dosyaları arayüzde 'Klasöre Taşı' butonunu kullanarak organize edebilir, kendi klasör yapınızı bilgisayara kaydetmeden önce oluşturabilirsiniz."
        )
        tk.Label(tab2, text=t2_text, bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=720).pack(fill=tk.BOTH, expand=True)
        
        # Tab 3: Performans ve Çoklu Motor
        tab3 = tk.Frame(notebook, bg="#FFFFFF", padx=20, pady=20)
        notebook.add(tab3, text="Çoklu Motor & Performans")
        
        t3_text = (
            "📌 Paralel Motorlarla Tarama (Concurrent Multi-threading)\n\n"
            "Programımız, diski bağımsız parçalara (örneğin 100 GB'lık bölümlere) ayırarak her bölümü farklı bir iş parçacığının (thread) taramasını sağlar. "
            "Bu sayede donanım limitlerindeki hızlara ulaşılır.\n\n"
            "Tavsiye Edilen Motor Sayıları:\n"
            "  • Mekanik Sabit Diskler (HDD): 1 veya 2 Motor. Disk kafası fiziksel olarak seek/read yaptığı için çok fazla thread diski yavaşlatır.\n"
            "  • SSD ve NVMe Sürücüler: 4 ile 8 Motor arası. Eşzamanlı okuma kapasiteleri çok yüksek olduğundan tarama süresi ciddi şekilde kısalır.\n"
            "  • Özel Aralık Taraması: Sadece belirli bir disk bölgesinde (Örn: 200. GB ile 300. GB arası) tarama yaparak saatler kazanabilirsiniz."
        )
        tk.Label(tab3, text=t3_text, bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=720).pack(fill=tk.BOTH, expand=True)
        
        # Tab 4: Otomatik Onarım ve Dosya Analizi
        tab4 = tk.Frame(notebook, bg="#FFFFFF", padx=20, pady=20)
        notebook.add(tab4, text="Otomatik Dosya Onarımı")
        
        t4_text = (
            "📌 Gelişmiş Dosya Tamir Mekanizmaları\n\n"
            "Kurtarılan dosyaların çoğu disk üzerindeki bozulmalar nedeniyle açılmayabilir. Sistemimiz arka planda şu onarımları gerçekleştirir:\n\n"
            "  🛠️ JPEG Onarımı:\n"
            "  Sektör hizalamalarından kaynaklanan fazlalık boşlukları (null padding) temizler ve eksik bitiş imzasını (FFD9) otomatik ekleyerek resmin yarıda kesilmesini veya açılmamasını önler.\n\n"
            "  🛠️ MP4 Video Onarımı (Annex B Ayıklama):\n"
            "  Biçimlendirilen videolarda 'moov atom' kaybolur ve oynatıcılar videoyu açamaz. Programımız ham video karelerini (byte stream) tarayarak çalışabilir bir '.h264' video akışı ayıklar."
        )
        tk.Label(tab4, text=t4_text, bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 10), justify="left", anchor="nw", wraplength=720).pack(fill=tk.BOTH, expand=True)
        
        # Tab 5: Önizleme Ayarları & Kontrol Paneli
        tab5 = tk.Frame(notebook, bg="#FFFFFF", padx=20, pady=20)
        notebook.add(tab5, text="Önizleme Kontrol Paneli")
        
        # Title
        tk.Label(tab5, text="⚙️ Önizleme Doğrulama ve Filtreleme Ayarları", bg="#FFFFFF", fg="#1E1E24", font=("Segoe UI", 11, "bold"), anchor="w").pack(fill=tk.X, pady=(0, 10))
        
        # Frame for controls
        ctrl_frame = tk.Frame(tab5, bg="#FFFFFF")
        ctrl_frame.pack(fill=tk.X, pady=5)
        
        # Strictness level
        tk.Label(ctrl_frame, text="Doğrulama Seviyesi:", bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 9, "bold")).grid(row=0, column=0, sticky="w", pady=5)
        
        if not hasattr(self, "preview_strictness_var"):
            self.preview_strictness_var = tk.StringVar(value="Normal")
            
        strictness_combo = ttk.Combobox(ctrl_frame, textvariable=self.preview_strictness_var, values=["Hızlı (Sadece Başlık)", "Normal (Sıfır Blok Filtresi)", "Sıkı (Detaylı Piksel & Kodlama Analizi)"], state="readonly", width=35)
        strictness_combo.grid(row=0, column=1, sticky="w", padx=10, pady=5)
        
        # Minimum preview size
        tk.Label(ctrl_frame, text="Min. Önizleme Boyutu (Byte):", bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 9, "bold")).grid(row=1, column=0, sticky="w", pady=5)
        
        if not hasattr(self, "min_preview_size_var"):
            self.min_preview_size_var = tk.StringVar(value="512")
            
        min_size_entry = ttk.Entry(ctrl_frame, textvariable=self.min_preview_size_var, width=15)
        min_size_entry.grid(row=1, column=1, sticky="w", padx=10, pady=5)
        
        # Auto exclude corrupt files check button
        if not hasattr(self, "auto_exclude_corrupt_var"):
            self.auto_exclude_corrupt_var = tk.BooleanVar(value=True)
            
        chk_exclude = tk.Checkbutton(ctrl_frame, text="Bozuk/Eksik Verileri Listeden Otomatik Olarak Ayıkla (Önizlenemez Yap)", variable=self.auto_exclude_corrupt_var, bg="#FFFFFF", activebackground="#FFFFFF", fg="#2F3542", font=("Segoe UI", 9))
        chk_exclude.grid(row=2, column=0, columnspan=2, sticky="w", pady=10)
        
        # Stats Frame
        stats_frame = tk.LabelFrame(tab5, text=" Önizleme İstatistikleri ", bg="#FFFFFF", fg="#1E1E24", font=("Segoe UI", 9, "bold"), padx=10, pady=10)
        stats_frame.pack(fill=tk.X, pady=15)
        
        # Calculate stats on the fly
        total_files = len(self.virtual_files)
        previewable_count = sum(1 for f in self.virtual_files if f.get("is_previewable", False))
        non_previewable_count = total_files - previewable_count
        
        lbl_total = tk.Label(stats_frame, text=f"Toplam Bulunan Dosya: {total_files}", bg="#FFFFFF", fg="#2F3542", font=("Segoe UI", 9))
        lbl_total.pack(anchor="w", pady=2)
        lbl_prev = tk.Label(stats_frame, text=f"Önizlemesi Doğrulanan Dosyalar: {previewable_count}", bg="#FFFFFF", fg="#2ECC71", font=("Segoe UI", 9, "bold"))
        lbl_prev.pack(anchor="w", pady=2)
        lbl_non_prev = tk.Label(stats_frame, text=f"Bozuk veya Önizlenemeyen Dosyalar: {non_previewable_count}", bg="#FFFFFF", fg="#FF4757", font=("Segoe UI", 9, "bold"))
        lbl_non_prev.pack(anchor="w", pady=2)
        
        # Description
        desc_lbl = tk.Label(tab5, text="* Not: Sıkı modda Pillow kütüphanesi tüm piksel verisini çözerek doğrular. Çok büyük dosya listelerinde bu mod taramayı değil sadece önizleme listeleme hızını etkiler.", bg="#FFFFFF", fg="#7F8C8D", font=("Segoe UI", 8, "italic"), justify="left", wraplength=720)
        desc_lbl.pack(fill=tk.X, pady=(10, 0))
        
        close_btn = tk.Button(help_win, text="Kapat", command=help_win.destroy, bg="#2F3542", fg="#FFFFFF", borderwidth=0, padx=20, pady=8, font=("Segoe UI", 9, "bold"))
        close_btn.pack(pady=10)

    def select_output_directory(self):
        import os
        from tkinter import filedialog, messagebox
        selected_drive = self.active_drive
        if not selected_drive:
            selected_disp = self.drive_var.get()
            if selected_disp and selected_disp != "Diskler aranıyor...":
                selected_drive = self.drives_map.get(selected_disp)
                
        initial_dir = self.selected_output_dir
        if not initial_dir or initial_dir.startswith("C:\\"):
            suggested_root = self.get_default_target_drive_root()
            if suggested_root:
                initial_dir = suggested_root
                
        directory = filedialog.askdirectory(initialdir=initial_dir, title="Taşınacak Yeri Seçin")
        if directory:
            abs_dir = os.path.abspath(directory)
            if selected_drive and self.is_same_disk(selected_drive, abs_dir):
                messagebox.showerror(
                    "Kritik Hata: Aynı Disk Seçilemez!", 
                    "Hata: Kurtarma yapmak istediğiniz hedef disk ile kaynak disk aynı fiziksel disk üzerindedir!\n\n"
                    "Verilerin üst üste yazılmasını (overwrite) ve kalıcı veri kaybını önlemek için kurtarma konumunu farklı bir fiziksel diske (örneğin harici bir USB bellek veya farklı bir sürücü) ayarlamalısınız."
                )
                return
            self.selected_output_dir = abs_dir
            self.path_lbl.config(text=self.selected_output_dir)
            self.update_target_drive_status()
            if getattr(self, "current_session_file", None) is not None:
                self.save_scan_state()

    def toggle_dashboard_log(self):
        if self.dash_log_visible:
            self.dash_log_panel.pack_forget()
            self.toggle_log_btn.config(text="📖 Terminal Logunu Göster")
            self.dash_log_visible = False
        else:
            self.dash_log_panel.pack(fill=tk.BOTH, expand=True)
            self.toggle_log_btn.config(text="📕 Terminal Logunu Gizle")
            self.dash_log_visible = True
            
            # Sync logs
            try:
                self.dash_log_text.config(state="normal")
                self.dash_log_text.delete("1.0", tk.END)
                self.dash_log_text.insert(tk.END, "".join(self.console_logs))
                self.dash_log_text.config(state="disabled")
                self.dash_log_text.see(tk.END)
            except:
                pass

    def update_system_stats(self):
        import ctypes
        import subprocess
        import threading
        
        # 1. RAM Usage (via GlobalMemoryStatusEx)
        class MEMORYSTATUSEX(ctypes.Structure):
            _fields_ = [
                ("dwLength", ctypes.c_ulong),
                ("dwMemoryLoad", ctypes.c_ulong),
                ("ullTotalPhys", ctypes.c_ulonglong),
                ("ullAvailPhys", ctypes.c_ulonglong),
                ("ullTotalPageFile", ctypes.c_ulonglong),
                ("ullAvailPageFile", ctypes.c_ulonglong),
                ("ullTotalVirtual", ctypes.c_ulonglong),
                ("ullAvailVirtual", ctypes.c_ulonglong),
                ("ullAvailExtendedVirtual", ctypes.c_ulonglong)
            ]
        try:
            stat = MEMORYSTATUSEX()
            stat.dwLength = ctypes.sizeof(stat)
            ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(stat))
            total_gb = stat.ullTotalPhys / (1024 * 1024 * 1024)
            used_gb = (stat.ullTotalPhys - stat.ullAvailPhys) / (1024 * 1024 * 1024)
            ram_pct = int(stat.dwMemoryLoad)
            ram_str = f"RAM: {used_gb:.2f} GB / {total_gb:.2f} GB ({ram_pct}%)"
        except:
            ram_pct = 30
            ram_str = "RAM: Bilinmiyor"
            
        # 2. CPU/GPU Usage & Temperature (asynchronous/non-blocking)
        # Query via separate threads to keep Tkinter GUI responsive
        def run_queries():
            # CPU Load via GetSystemTimes (0% CPU overhead, no PowerShell process spawn)
            cpu_val = 0
            cpu_str = "CPU Yükü: Bilinmiyor"
            class FILETIME(ctypes.Structure):
                _fields_ = [("dwLowDateTime", ctypes.c_uint), ("dwHighDateTime", ctypes.c_uint)]
                
            def to_int(ft):
                return (ft.dwHighDateTime << 32) + ft.dwLowDateTime
                
            idle1 = FILETIME()
            kernel1 = FILETIME()
            user1 = FILETIME()
            
            if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle1), ctypes.byref(kernel1), ctypes.byref(user1)):
                time.sleep(0.15)
                idle2 = FILETIME()
                kernel2 = FILETIME()
                user2 = FILETIME()
                if ctypes.windll.kernel32.GetSystemTimes(ctypes.byref(idle2), ctypes.byref(kernel2), ctypes.byref(user2)):
                    idle = to_int(idle2) - to_int(idle1)
                    kernel = to_int(kernel2) - to_int(kernel1)
                    user = to_int(user2) - to_int(user1)
                    total = kernel + user
                    if total > 0:
                        active = total - idle
                        cpu_val = max(0, min(100, (active * 100) // total))
                        cpu_str = f"CPU Yükü: %{cpu_val}"
            
            # GPU Name (Cached so we only query once at startup)
            if not hasattr(self, "gpu_name_cached"):
                try:
                    cmd_gpu = "powershell -Command \"(Get-CimInstance Win32_VideoController).Name\""
                    res_gpu = subprocess.run(cmd_gpu, capture_output=True, text=True, shell=True, timeout=1.0)
                    if res_gpu.returncode == 0 and res_gpu.stdout.strip():
                        gpu_name = res_gpu.stdout.strip().split('\n')[0].strip()
                        self.gpu_name_cached = f"GPU: {gpu_name} (Aktif)"
                    else:
                        self.gpu_name_cached = "GPU: Devre Dışı / Bulunamadı"
                except:
                    self.gpu_name_cached = "GPU: Aktif"
            gpu_str = self.gpu_name_cached
            
            # CPU Temp (Query only once every 10 seconds to save CPU cycles)
            temp_str = "CPU Sıcaklığı: Normal"
            curr_t = time.time()
            if curr_t - getattr(self, "last_temp_check_time", 0.0) >= 10.0:
                self.last_temp_check_time = curr_t
                try:
                    cmd_temp = "powershell -Command \"Get-CimInstance -Namespace root/wmi -ClassName MsAcpi_ThermalZoneTemperature | Select-Object -ExpandProperty CurrentTemperature\""
                    res_temp = subprocess.run(cmd_temp, capture_output=True, text=True, shell=True, timeout=1.0)
                    if res_temp.returncode == 0 and res_temp.stdout.strip():
                        temps = [float(t) for t in res_temp.stdout.strip().split() if t.strip().isdigit()]
                        if temps:
                            celsius_temps = [(t / 10) - 273.15 for t in temps]
                            avg_temp = sum(celsius_temps) / len(celsius_temps)
                            if 10 <= avg_temp <= 110:
                                self.last_temp_str_cached = f"CPU Sıcaklığı: {avg_temp:.1f}°C"
                            else:
                                self.last_temp_str_cached = "CPU Sıcaklığı: Normal"
                        else:
                            self.last_temp_str_cached = "CPU Sıcaklığı: Normal"
                    else:
                        self.last_temp_str_cached = "CPU Sıcaklığı: Normal"
                except:
                    self.last_temp_str_cached = "CPU Sıcaklığı: Normal"
            
            temp_str = getattr(self, "last_temp_str_cached", "CPU Sıcaklığı: Normal")
                
            # Safely schedule labels updates on main thread
            self.after(0, lambda: self.apply_system_stats(ram_str, cpu_str, temp_str, gpu_str, ram_pct, cpu_val))
            
        threading.Thread(target=run_queries, daemon=True).start()
        self.after(2000, self.update_system_stats) # Update every 2 seconds to prevent CPU overhead from PowerShell

    def apply_system_stats(self, ram_str, cpu_str, temp_str, gpu_str, ram_pct=0, cpu_val=0):
        if hasattr(self, "ram_lbl") and self.ram_lbl:
            self.ram_lbl.config(text=ram_str)
        if hasattr(self, "cpu_lbl") and self.cpu_lbl:
            self.cpu_lbl.config(text=cpu_str)
        if hasattr(self, "gpu_lbl") and self.gpu_lbl:
            self.gpu_lbl.config(text=gpu_str)
        if hasattr(self, "temp_lbl") and self.temp_lbl:
            self.temp_lbl.config(text=temp_str)
            
        # Determine load level (max of CPU and RAM percentages)
        load_val = max(cpu_val, ram_pct)
        
        # 4 different levels:
        # - Rahat (Comfortable - Green): Load < 50%
        # - Hafif Yoğun (Lightly Busy - Blue): 50% <= Load < 70%
        # - Orta Yoğun (Moderately Busy - Orange): 70% <= Load < 85%
        # - Çok Yoğun (Very Busy - Red): Load >= 85%
        if load_val < 50:
            status_text = "Sistem Durumu: Rahat (En Optimize Hız)"
            status_color = "#2ECC71" # Green
            delay_target = 0.00
        elif load_val < 70:
            status_text = "Sistem Durumu: Hafif Yoğun (Hız Sınırlı - %10)"
            status_color = "#3498DB" # Blue
            delay_target = 0.001
        elif load_val < 85:
            status_text = "Sistem Durumu: Orta Yoğun (Hız Sınırlı - %35)"
            status_color = "#E67E22" # Orange
            delay_target = 0.005
        else:
            status_text = "Sistem Durumu: Çok Yoğun (Hız Sınırlı - %70)"
            status_color = "#E74C3C" # Red
            delay_target = 0.020
            
        self.scan_delay = delay_target
        if hasattr(self, "engine_lbl") and self.engine_lbl:
            self.engine_lbl.config(text=status_text, fg=status_color)

    def toggle_dash_adv_panel(self):
        if self.dash_show_adv_var.get():
            self.category_select_bar.pack(fill=tk.X, pady=(0, 15), before=self.scan_header_lbl)
        else:
            self.category_select_bar.pack_forget()

    def toggle_parallel_options(self):
        is_active_scanning = getattr(self, "is_scanning", False) and not getattr(self, "scan_paused", False)
        if is_active_scanning:
            # Disable inputs mid-scan only if actively scanning (not paused)
            self.parallel_cb.config(state="disabled")
            self.worker_combo.config(state="disabled")
            self.segment_entry.config(state="disabled")
            self.custom_range_cb.config(state="disabled")
            self.custom_block_entry.config(state="disabled")
            if hasattr(self, "unscanned_cb"):
                self.unscanned_cb.config(state="disabled")
            if hasattr(self, "scan_from_end_cb"):
                self.scan_from_end_cb.config(state="disabled")
            for cb in getattr(self, "category_checkboxes", []):
                cb.config(state="disabled")
        else:
            self.parallel_cb.config(state="normal")
            self.custom_range_cb.config(state="normal")
            if hasattr(self, "unscanned_cb"):
                self.unscanned_cb.config(state="normal")
            if hasattr(self, "scan_from_end_cb"):
                self.scan_from_end_cb.config(state="normal")
            for cb in getattr(self, "category_checkboxes", []):
                cb.config(state="normal")
            
            state = "normal" if self.use_parallel_var.get() else "disabled"
            self.worker_combo.config(state=state if state == "disabled" else "readonly")
            self.segment_entry.config(state=state)
            
            range_state = "normal" if self.use_custom_range_var.get() else "disabled"
            self.custom_block_entry.config(state=range_state)

    def draw_disk_map(self):
        if not hasattr(self, "disk_map_canvas") or not self.disk_map_canvas:
            return
            
        canvas_w = self.disk_map_canvas.winfo_width()
        canvas_h = self.disk_map_canvas.winfo_height()
        if canvas_w < 10: canvas_w = 600
        if canvas_h < 10: canvas_h = 60
        
        self.disk_map_canvas.delete("all")
        
        total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
        
        cols = 100
        rows = 1
        total_blocks = cols * rows
        
        pad_x = 1
        pad_y = 0
        block_w = (canvas_w - (cols + 1) * pad_x) / cols
        block_h = 24  # Single row thickness
        
        scanned_intervals = []
        try:
            segment_size_gb = float(self.segment_size_gb_var.get())
            if segment_size_gb <= 0: segment_size_gb = 100.0
        except:
            segment_size_gb = 100.0
        segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)

        if hasattr(self, "segment_progress") and self.segment_progress:
            with self.segment_lock:
                for seg_start, prog in self.segment_progress.items():
                    seg_end = seg_start + segment_size_bytes
                    if hasattr(self, "segment_bounds") and self.segment_bounds:
                        if seg_start in self.segment_bounds:
                            seg_end = self.segment_bounds[seg_start]
                    elif hasattr(self, "scan_segments") and self.scan_segments:
                        for start, end in self.scan_segments:
                            if start == seg_start:
                                seg_end = end
                                break
                    if seg_end > total_size:
                        seg_end = total_size
                    scanned_intervals.append((seg_start, seg_start + prog, seg_end))
                    
        y1 = (canvas_h - block_h) / 2
        y2 = y1 + block_h
        
        for c in range(cols):
            block_start = (c / total_blocks) * total_size
            block_end = ((c + 1) / total_blocks) * total_size
            
            total_scanned_in_block = 0
            is_currently_scanning = False
            
            for seg_start, seg_scanned, seg_end in scanned_intervals:
                overlap_start = max(block_start, seg_start)
                overlap_end = min(block_end, seg_scanned)
                if overlap_end > overlap_start:
                    total_scanned_in_block += (overlap_end - overlap_start)
                
                if getattr(self, "is_scanning", False) and seg_scanned > seg_start and seg_scanned < seg_end:
                    if block_start <= seg_scanned <= block_end:
                        is_currently_scanning = True
            
            block_len = block_end - block_start
            scanned_pct = total_scanned_in_block / block_len if block_len > 0 else 0
            
            if scanned_pct >= 0.95:
                color = "#10AC84"  # Scanned (Emerald Green)
            elif is_currently_scanning:
                color = "#FF9F43"  # Scanning (Orange)
            else:
                color = "#2F3542"  # Unscanned (Dark Blue/Gray)
                
            x1 = pad_x + c * (block_w + pad_x)
            x2 = x1 + block_w
            
            if hasattr(self, "selected_canvas_blocks") and (c + 1) in self.selected_canvas_blocks:
                outline_color = "#00CEC9"
                outline_width = 2
            else:
                outline_color = "#57606F" if color == "#2F3542" else color
                outline_width = 1

            self.disk_map_canvas.create_rectangle(
                x1, y1, x2, y2,
                fill=color,
                outline=outline_color,
                width=outline_width
            )

    def on_disk_map_hover(self, event):
        if not self.active_drive:
            return
            
        canvas_w = self.disk_map_canvas.winfo_width()
        canvas_h = self.disk_map_canvas.winfo_height()
        if canvas_w < 10: canvas_w = 600
        if canvas_h < 10: canvas_h = 60
        
        cols = 100
        pad_x = 1
        block_w = (canvas_w - (cols + 1) * pad_x) / cols
        
        x = event.x
        col = int(x / (block_w + pad_x))
        if col < 0: col = 0
        if col >= cols: col = cols - 1
        
        total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
        block_start = (col / cols) * total_size
        block_end = ((col + 1) / cols) * total_size
        
        start_gb = block_start / (1024 * 1024 * 1024)
        end_gb = block_end / (1024 * 1024 * 1024)
        
        scanned_intervals = []
        try:
            segment_size_gb = float(self.segment_size_gb_var.get())
            if segment_size_gb <= 0: segment_size_gb = 100.0
        except:
            segment_size_gb = 100.0
        segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)

        if hasattr(self, "segment_progress") and self.segment_progress:
            with self.segment_lock:
                for seg_start, prog in self.segment_progress.items():
                    seg_end = seg_start + segment_size_bytes
                    if hasattr(self, "segment_bounds") and self.segment_bounds:
                        if seg_start in self.segment_bounds:
                            seg_end = self.segment_bounds[seg_start]
                    elif hasattr(self, "scan_segments") and self.scan_segments:
                        for start, end in self.scan_segments:
                            if start == seg_start:
                                seg_end = end
                                break
                    if seg_end > total_size:
                        seg_end = total_size
                    scanned_intervals.append((seg_start, seg_start + prog, seg_end))
                    
        total_scanned_in_block = 0
        is_currently_scanning = False
        
        for seg_start, seg_scanned, seg_end in scanned_intervals:
            overlap_start = max(block_start, seg_start)
            overlap_end = min(block_end, seg_scanned)
            if overlap_end > overlap_start:
                total_scanned_in_block += (overlap_end - overlap_start)
            
            if seg_scanned > seg_start and seg_scanned < seg_end:
                if block_start <= seg_scanned <= block_end:
                    is_currently_scanning = True
                    
        block_len = block_end - block_start
        scanned_pct = total_scanned_in_block / block_len if block_len > 0 else 0
        
        if is_currently_scanning:
            status = "Taranıyor"
        elif scanned_pct >= 0.95:
            status = "Tarandı (%100)"
        elif scanned_pct > 0.05:
            status = f"Kısmen Tarandı (%{scanned_pct*100:.1f})"
        else:
            status = "Taranmadı"
            
        self.draw_disk_map()
        
        y1 = (canvas_h - 24) / 2
        y2 = y1 + 24
        x1 = pad_x + col * (block_w + pad_x)
        x2 = x1 + block_w
        
        self.disk_map_canvas.create_rectangle(
            x1, y1, x2, y2,
            outline="#FFFFFF",
            width=2
        )
        
        tooltip_text = f"Blok {col+1}/100: {start_gb:.2f} GB - {end_gb:.2f} GB | Durum: {status} (Detaylar için tıklayın)"
        self.disk_map_canvas.create_text(
            canvas_w / 2, canvas_h - 8,
            text=tooltip_text,
            fill="#FFFFFF",
            font=("Segoe UI", 8, "bold")
        )

    def on_disk_map_leave(self, event):
        self.draw_disk_map()

    def on_disk_map_click(self, event):
        if not getattr(self, "active_drive", None):
            messagebox.showwarning("Uyarı", "Lütfen önce kurtarma yapılacak bir disk seçin veya tarama başlatın.")
            return
            
        canvas_w = self.disk_map_canvas.winfo_width()
        if canvas_w < 10: canvas_w = 600
        cols = 100
        pad_x = 1
        block_w = (canvas_w - (cols + 1) * pad_x) / cols
        
        x = event.x
        col = int(x / (block_w + pad_x))
        if col < 0: col = 0
        if col >= cols: col = cols - 1
        block_num = col + 1
        
        if not hasattr(self, "selected_canvas_blocks"):
            self.selected_canvas_blocks = set()
        if not hasattr(self, "last_clicked_block"):
            self.last_clicked_block = None
            
        is_shift = bool(event.state & 0x0001)
        is_ctrl = bool(event.state & 0x0004)
        
        if is_ctrl:
            if block_num in self.selected_canvas_blocks:
                self.selected_canvas_blocks.remove(block_num)
            else:
                self.selected_canvas_blocks.add(block_num)
            self.last_clicked_block = block_num
        elif is_shift and self.last_clicked_block is not None:
            start = min(self.last_clicked_block, block_num)
            end = max(self.last_clicked_block, block_num)
            self.selected_canvas_blocks.clear()
            for b in range(start, end + 1):
                self.selected_canvas_blocks.add(b)
        else:
            self.selected_canvas_blocks.clear()
            self.selected_canvas_blocks.add(block_num)
            self.last_clicked_block = block_num
            
        block_list = sorted(list(self.selected_canvas_blocks))
        if block_list:
            ranges = []
            start_b = block_list[0]
            prev_b = block_list[0]
            for num in block_list[1:]:
                if num == prev_b + 1:
                    prev_b = num
                else:
                    if start_b == prev_b:
                        ranges.append(str(start_b))
                    else:
                        ranges.append(f"{start_b}-{prev_b}")
                    start_b = num
                    prev_b = num
            if start_b == prev_b:
                ranges.append(str(start_b))
            else:
                ranges.append(f"{start_b}-{prev_b}")
            range_str = ", ".join(ranges)
            
            self.use_custom_range_var.set(True)
            self.custom_block_range_var.set(range_str)
        else:
            self.use_custom_range_var.set(False)
            self.custom_block_range_var.set("")
            
        if hasattr(self, "toggle_parallel_options"):
            self.toggle_parallel_options()
        if hasattr(self, "toggle_gallery_adv_options"):
            self.toggle_gallery_adv_options()
            
        self.draw_disk_map()

    def on_disk_map_double_click(self, event):
        if not getattr(self, "active_drive", None):
            messagebox.showwarning("Uyarı", "Lütfen önce kurtarma yapılacak bir disk seçin veya tarama başlatın.")
            return
            
        from tkinter import Toplevel
        
        detail_win = Toplevel(self)
        detail_win.title("Disk Detaylı Durum Haritası Logu")
        detail_win.geometry("700x480")
        detail_win.configure(bg="#1E1E24")
        detail_win.transient(self)
        detail_win.grab_set()
        
        title_lbl = tk.Label(detail_win, text="Disk Detaylı Durum Haritası", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 12, "bold"))
        title_lbl.pack(anchor="w", padx=20, pady=15)
        
        desc_lbl = tk.Label(detail_win, text="Disk üzerindeki 100 bloğun detaylı tarama durumu aşağıda listelenmiştir:", bg="#1E1E24", fg="#A4B0BE", font=("Segoe UI", 9))
        desc_lbl.pack(anchor="w", padx=20, pady=(0, 10))
        
        list_frame = tk.Frame(detail_win, bg="#1E1E24")
        list_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=5)
        
        pane = tk.PanedWindow(list_frame, orient=tk.HORIZONTAL, bg="#1E1E24", sashwidth=4)
        pane.pack(fill=tk.BOTH, expand=True)
        
        # Left Panel (Block list)
        left_panel = tk.Frame(pane, bg="#1E1E24")
        pane.add(left_panel, minsize=450)
        
        scroll_y = ttk.Scrollbar(left_panel, orient="vertical")
        scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        style = ttk.Style()
        style.configure("Details.Treeview", background="#2F3542", foreground="#FFFFFF", fieldbackground="#2F3542", font=("Segoe UI", 9))
        
        tree = ttk.Treeview(left_panel, selectmode="extended", style="Details.Treeview", yscrollcommand=scroll_y.set)
        tree.pack(fill=tk.BOTH, expand=True)
        scroll_y.config(command=tree.yview)
        
        # Right Panel (Queue / Playlist)
        right_panel = tk.Frame(pane, bg="#1E1E24", padx=10)
        pane.add(right_panel, minsize=220)
        
        queue_lbl = tk.Label(right_panel, text="Tarama Kuyruğu (Sıralı)", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"))
        queue_lbl.pack(anchor="w", pady=(0, 5))
        
        queue_listbox = tk.Listbox(
            right_panel, 
            bg="#2F3542", 
            fg="#FFFFFF", 
            selectbackground=self.accent_blue, 
            selectforeground="#FFFFFF",
            font=("Segoe UI", 9), 
            borderwidth=0, 
            highlightthickness=0,
            selectmode=tk.SINGLE
        )
        queue_listbox.pack(fill=tk.BOTH, expand=True, pady=2)
        
        # Queue buttons
        q_btn_frame = tk.Frame(right_panel, bg="#1E1E24")
        q_btn_frame.pack(fill=tk.X, pady=(5, 0))
        
        def get_block_pct(block_num):
            total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
            cols = 100
            i = block_num - 1
            block_start = (i / cols) * total_size
            block_end = ((i + 1) / cols) * total_size
            
            try:
                segment_size_gb = float(self.segment_size_gb_var.get())
                if segment_size_gb <= 0: segment_size_gb = 100.0
            except:
                segment_size_gb = 100.0
            segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)
            
            scanned_intervals = []
            if hasattr(self, "segment_progress") and self.segment_progress:
                with self.segment_lock:
                    for seg_start, prog in self.segment_progress.items():
                        seg_end = seg_start + segment_size_bytes
                        if hasattr(self, "segment_bounds") and self.segment_bounds and seg_start in self.segment_bounds:
                            seg_end = self.segment_bounds[seg_start]
                        if seg_end > total_size:
                            seg_end = total_size
                        scanned_intervals.append((seg_start, seg_start + prog, seg_end))
                        
            total_scanned_in_block = 0
            for seg_start, seg_scanned, seg_end in scanned_intervals:
                overlap_start = max(block_start, seg_start)
                overlap_end = min(block_end, seg_scanned)
                if overlap_end > overlap_start:
                    total_scanned_in_block += (overlap_end - overlap_start)
            block_len = block_end - block_start
            return (total_scanned_in_block / block_len) * 100

        def refresh_queue_listbox():
            queue_listbox.delete(0, tk.END)
            for idx, b_num in enumerate(self.scan_queue):
                pct = get_block_pct(b_num)
                queue_listbox.insert(tk.END, f"{idx+1}. Blok {b_num} (%{pct:.1f})")

        def add_to_queue():
            selected = tree.selection()
            added = False
            for sel in selected:
                block_num_str = tree.item(sel, "text")
                try:
                    b_num = int(block_num_str.replace("Blok", "").strip())
                    if b_num not in self.scan_queue:
                        self.scan_queue.append(b_num)
                        added = True
                except:
                    pass
            if added:
                self.save_app_settings()
                refresh_queue_listbox()
                self.populate_detail_map_tree(tree)

        def remove_from_queue():
            sel_idx = queue_listbox.curselection()
            if not sel_idx:
                return
            for idx in sorted(sel_idx, reverse=True):
                self.scan_queue.pop(idx)
            self.save_app_settings()
            refresh_queue_listbox()
            self.populate_detail_map_tree(tree)

        def move_up():
            sel_idx = queue_listbox.curselection()
            if not sel_idx:
                return
            idx = sel_idx[0]
            if idx > 0:
                self.scan_queue[idx], self.scan_queue[idx - 1] = self.scan_queue[idx - 1], self.scan_queue[idx]
                self.save_app_settings()
                refresh_queue_listbox()
                queue_listbox.select_set(idx - 1)
                self.populate_detail_map_tree(tree)

        def move_down():
            sel_idx = queue_listbox.curselection()
            if not sel_idx:
                return
            idx = sel_idx[0]
            if idx < len(self.scan_queue) - 1:
                self.scan_queue[idx], self.scan_queue[idx + 1] = self.scan_queue[idx + 1], self.scan_queue[idx]
                self.save_app_settings()
                refresh_queue_listbox()
                queue_listbox.select_set(idx + 1)
                self.populate_detail_map_tree(tree)

        def clear_queue():
            self.scan_queue.clear()
            self.save_app_settings()
            refresh_queue_listbox()
            self.populate_detail_map_tree(tree)

        add_btn = tk.Button(q_btn_frame, text="[+] Ekle", command=add_to_queue, bg="#10AC84", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 8, "bold"), pady=4)
        add_btn.grid(row=0, column=0, sticky="ew", padx=2, pady=2)
        
        rem_btn = tk.Button(q_btn_frame, text="[-] Çıkar", command=remove_from_queue, bg="#FF4757", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 8, "bold"), pady=4)
        rem_btn.grid(row=0, column=1, sticky="ew", padx=2, pady=2)
        
        up_btn = tk.Button(q_btn_frame, text="▲ Yukarı", command=move_up, bg="#2F3542", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 8, "bold"), pady=4)
        up_btn.grid(row=1, column=0, sticky="ew", padx=2, pady=2)
        
        down_btn = tk.Button(q_btn_frame, text="▼ Aşağı", command=move_down, bg="#2F3542", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 8, "bold"), pady=4)
        down_btn.grid(row=1, column=1, sticky="ew", padx=2, pady=2)
        
        clear_btn = tk.Button(q_btn_frame, text="Temizle", command=clear_queue, bg="#57606F", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 8, "bold"), pady=4)
        clear_btn.grid(row=2, column=0, columnspan=2, sticky="ew", padx=2, pady=2)
        
        q_btn_frame.columnconfigure(0, weight=1)
        q_btn_frame.columnconfigure(1, weight=1)

        refresh_queue_listbox()
        
        tree["columns"] = ("range", "scanned", "recovered", "copies", "unwanted", "status")
        tree.column("#0", width=80, anchor="center")
        tree.column("range", width=160, anchor="w")
        tree.column("scanned", width=100, anchor="center")
        tree.column("recovered", width=100, anchor="center")
        tree.column("copies", width=80, anchor="center")
        tree.column("unwanted", width=110, anchor="center")
        tree.column("status", width=90, anchor="center")
        
        tree.heading("#0", text="Blok No", anchor="center")
        tree.heading("range", text="Bellek Aralığı (GB)", anchor="w")
        tree.heading("scanned", text="Taranan Miktar", anchor="center")
        tree.heading("recovered", text="Bulunan Öğe", anchor="center")
        tree.heading("copies", text="Kopya", anchor="center")
        tree.heading("unwanted", text="İstem Dışı Öğe", anchor="center")
        tree.heading("status", text="Durum", anchor="center")
        
        tree.tag_configure("scanning", background="#D35400", foreground="#FFFFFF")
        tree.tag_configure("scanned", background="#10AC84", foreground="#FFFFFF")
        tree.tag_configure("partial", background="#2ECC71", foreground="#FFFFFF")
        tree.tag_configure("queued", background="#2980B9", foreground="#FFFFFF")
        tree.tag_configure("unscanned", background="#2F3542", foreground="#FFFFFF")
        
        self.detail_map_tree = tree
        self.populate_detail_map_tree(tree)
        
        tree.bind("<Destroy>", lambda e: setattr(self, "detail_map_tree", None))
        
        def run_selected_block():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Uyarı", "Lütfen listeden taramak istediğiniz bloğu seçin.")
                return
            block_nums = []
            for sel in selected:
                block_num_str = tree.item(sel, "text")
                try:
                    block_nums.append(int(block_num_str.replace("Blok", "").strip()))
                except:
                    pass
            if not block_nums:
                return
                
            block_nums.sort()
            
            # Clear scan queue since user selected a specific block to scan directly
            self.scan_queue = []
            self.save_app_settings()
            refresh_queue_listbox()
            
            # Sync with visual canvas selection
            self.selected_canvas_blocks = set(block_nums)
            self.last_clicked_block = block_nums[-1]
            
            # Group into ranges (e.g. [15, 16, 17, 25] -> "15-17, 25")
            ranges = []
            start = block_nums[0]
            prev = block_nums[0]
            
            for num in block_nums[1:]:
                if num == prev + 1:
                    prev = num
                else:
                    if start == prev:
                        ranges.append(str(start))
                    else:
                        ranges.append(f"{start}-{prev}")
                    start = num
                    prev = num
            if start == prev:
                ranges.append(str(start))
            else:
                ranges.append(f"{start}-{prev}")
                
            range_str = ", ".join(ranges)
            
            detail_win.destroy()
            
            # Setup custom block range and trigger scan
            self.use_custom_range_var.set(True)
            self.custom_block_range_var.set(range_str)
            
            # Update inputs state
            if hasattr(self, "toggle_parallel_options"):
                self.toggle_parallel_options()
            if hasattr(self, "toggle_gallery_adv_options"):
                self.toggle_gallery_adv_options()
                
            # If advanced settings panel is hidden, show it
            if hasattr(self, "dash_show_adv_var") and not self.dash_show_adv_var.get():
                self.dash_show_adv_var.set(True)
                self.toggle_dash_adv_panel()
                
            # React and switch scanning
            if getattr(self, "is_scanning", False):
                # Save state before switching blocks to back up current progress
                if hasattr(self, "save_scan_state"):
                    self.save_scan_state()
                
                # Terminate running threads
                self.is_scanning = False
                self.scan_paused = False
                self.status_lbl.config(text=f"Seçili blokların taranması için seans yönlendiriliyor...")
                
                def async_switch():
                    import time
                    # Wait for all ScanWorker threads to exit
                    while any(t.name == "ScanWorker" and t.is_alive() for t in threading.enumerate()):
                        time.sleep(0.05)
                    
                    # Set scanning state back to active
                    self.is_scanning = True
                    self.scan_paused = False
                    self.scan_segments = []  # Clear old segments to force recalculation
                    
                    # Resume recovery with the new block settings
                    self.resume_recovery()
                    
                import threading
                threading.Thread(target=async_switch, daemon=True).start()
            else:
                self.is_scanning = True
                self.scan_paused = False
                self.scan_segments = []
                if getattr(self, "current_session_file", None) is not None or getattr(self, "active_drive", None) is not None:
                    self.resume_recovery()
                else:
                    self.start_recovery()
                    
        def reset_selected_blocks():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Uyarı", "Lütfen sıfırlamak istediğiniz bloğu/blokları seçin.", parent=detail_win)
                return
            
            confirm = messagebox.askyesno("Onay", "Seçili blok(lar)ın tarama ilerlemesini sıfırlamak istediğinizden emin misiniz?", parent=detail_win)
            if not confirm:
                return

            total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
            cols = 100
            
            try:
                segment_size_gb = float(self.segment_size_gb_var.get())
                if segment_size_gb <= 0: segment_size_gb = 100.0
            except:
                segment_size_gb = 100.0
            segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)

            with self.segment_lock:
                for sel in selected:
                    block_num_str = tree.item(sel, "text")
                    try:
                        i = int(block_num_str.replace("Blok", "").strip()) - 1
                        block_start = (i / cols) * total_size
                        block_end = ((i + 1) / cols) * total_size
                        
                        # Find segments that overlap this block and reset progress
                        for seg_start in list(self.segment_progress.keys()):
                            seg_end = seg_start + segment_size_bytes
                            if hasattr(self, "segment_bounds") and self.segment_bounds and seg_start in self.segment_bounds:
                                seg_end = self.segment_bounds[seg_start]
                            
                            if max(block_start, seg_start) < min(block_end, seg_end):
                                self.segment_progress[seg_start] = 0
                                
                        # Reset copies and unwanted metrics for this block
                        if hasattr(self, "block_copy_counts"):
                            self.block_copy_counts[i] = 0
                        if hasattr(self, "block_unwanted_counts"):
                            self.block_unwanted_counts[i] = 0
                    except Exception as e:
                        print(f"Error resetting block: {e}")
                        
            self.draw_disk_map()
            self.populate_detail_map_tree(tree)

        def fill_selected_blocks():
            selected = tree.selection()
            if not selected:
                messagebox.showwarning("Uyarı", "Lütfen fullemek istediğiniz bloğu/blokları seçin.", parent=detail_win)
                return
            
            confirm = messagebox.askyesno("Onay", "Seçili blok(lar)ın tarama ilerlemesini %100 olarak işaretlemek istediğinizden emin misiniz?", parent=detail_win)
            if not confirm:
                return

            total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
            cols = 100
            
            try:
                segment_size_gb = float(self.segment_size_gb_var.get())
                if segment_size_gb <= 0: segment_size_gb = 100.0
            except:
                segment_size_gb = 100.0
            segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)

            with self.segment_lock:
                for sel in selected:
                    block_num_str = tree.item(sel, "text")
                    try:
                        i = int(block_num_str.replace("Blok", "").strip()) - 1
                        block_start = (i / cols) * total_size
                        block_end = ((i + 1) / cols) * total_size
                        
                        # Find segments that overlap this block and set progress to full
                        for seg_start in list(self.segment_progress.keys()):
                            seg_end = seg_start + segment_size_bytes
                            if hasattr(self, "segment_bounds") and self.segment_bounds and seg_start in self.segment_bounds:
                                seg_end = self.segment_bounds[seg_start]
                            
                            if max(block_start, seg_start) < min(block_end, seg_end):
                                self.segment_progress[seg_start] = seg_end - seg_start
                    except Exception as e:
                        print(f"Error filling block: {e}")
                        
            self.draw_disk_map()
            self.populate_detail_map_tree(tree)

        tree.bind("<Double-1>", lambda e: run_selected_block())
        
        btn_frame = tk.Frame(detail_win, bg="#1E1E24", pady=12)
        btn_frame.pack(fill=tk.X)
        
        def run_queue():
            if not self.scan_queue:
                messagebox.showwarning("Uyarı", "Tarama kuyruğu boş! Lütfen listeden barları seçip [+] Ekle butonuyla kuyruğa ekleyin.")
                return
            
            detail_win.destroy()
            self.use_custom_range_var.set(True)
            range_str = ", ".join(str(x) for x in self.scan_queue)
            self.custom_block_range_var.set(range_str)
            self.selected_canvas_blocks = set(self.scan_queue)
            self.last_clicked_block = self.scan_queue[-1]
            self.scan_segments = []
            self.resume_recovery()

        close_btn = tk.Button(btn_frame, text="İptal / Kapat", command=detail_win.destroy, bg="#57606F", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8, cursor="hand2")
        close_btn.pack(side=tk.RIGHT, padx=(10, 20))
        
        scan_queue_btn = tk.Button(btn_frame, text="Kuyruğu Tara", command=run_queue, bg="#FF9F43", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 9, "bold"), padx=18, pady=8, cursor="hand2")
        scan_queue_btn.pack(side=tk.RIGHT, padx=10)

        scan_block_btn = tk.Button(btn_frame, text="Seçili Bloğu Tara", command=run_selected_block, bg=self.accent_blue, fg=self.text_white, borderwidth=0, font=("Segoe UI", 9, "bold"), padx=18, pady=8, cursor="hand2")
        scan_block_btn.pack(side=tk.RIGHT, padx=10)
        
        fill_block_btn = tk.Button(btn_frame, text="Seçiliyi Fulle", command=fill_selected_blocks, bg="#10AC84", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8, cursor="hand2")
        fill_block_btn.pack(side=tk.LEFT, padx=(20, 10))
        
        reset_block_btn = tk.Button(btn_frame, text="Seçiliyi Sıfırla", command=reset_selected_blocks, bg="#FF4757", fg="#FFFFFF", borderwidth=0, font=("Segoe UI", 9, "bold"), padx=15, pady=8, cursor="hand2")
        reset_block_btn.pack(side=tk.LEFT)

    def show_scan_progress_modal(self):
        from tkinter import Toplevel
        
        if getattr(self, "scan_modal", None) and self.scan_modal.winfo_exists():
            self.scan_modal.lift()
            return

        self.scan_modal = Toplevel(self)
        self.scan_modal.title("⚡ NovaRecovery - Klasör Yapısı ve Canlı Tarama Paneli")
        self.scan_modal.geometry("960x680")
        self.scan_modal.configure(bg="#1E1E24")
        self.scan_modal.transient(self)
        
        # Header title
        header_frame = tk.Frame(self.scan_modal, bg="#1E1E24", padx=20, pady=12)
        header_frame.pack(fill=tk.X)
        
        selected_disp = self.drive_var.get() if hasattr(self, "drive_var") and self.drive_var.get() else "Seagate FireCuda HDD (1863.02 GB)"
        clean_name = selected_disp.split(":")[1].strip() if ":" in selected_disp else selected_disp
        drive_total_gb = (self.active_drive_size / (1024 * 1024 * 1024)) if getattr(self, "active_drive_size", 0) > 0 else 1863.02
        
        title_lbl = tk.Label(
            header_frame, 
            text="⚡ Klasör Yapısı ve Canlı Disk Tarama Paneli", 
            bg="#1E1E24", 
            fg="#00CEC9", 
            font=("Segoe UI", 14, "bold")
        )
        title_lbl.pack(anchor="w")
        
        sub_lbl = tk.Label(
            header_frame, 
            text=f'Seçili Cihaz: {clean_name}  |  Toplam Kapasite: {drive_total_gb:.2f} GB ({drive_total_gb/1024:.2f} TB)', 
            bg="#1E1E24", 
            fg="#A4B0BE", 
            font=("Segoe UI", 10, "bold")
        )
        sub_lbl.pack(anchor="w", pady=(3, 0))

        # Main Start / Control bar inside modal
        action_bar = tk.Frame(self.scan_modal, bg="#2F3542", padx=15, pady=10)
        action_bar.pack(fill=tk.X, padx=20, pady=(0, 10))

        self.modal_start_btn = tk.Button(
            action_bar, 
            text="🚀 TARAMAYI BAŞLAT", 
            command=self.trigger_modal_start_recovery, 
            bg="#10AC84", 
            fg="#FFFFFF", 
            font=("Segoe UI", 11, "bold"), 
            padx=20, 
            pady=6, 
            borderwidth=0,
            cursor="hand2"
        )
        self.modal_start_btn.pack(side=tk.LEFT, padx=(0, 15))

        self.modal_heartbeat_lbl = tk.Label(
            action_bar, 
            text="🟢 Canlı Sayaç: 0 sn (Beklemede)", 
            bg="#1E1E24", 
            fg="#00FF66", 
            font=("Consolas", 10, "bold"), 
            padx=12, 
            pady=6
        )
        self.modal_heartbeat_lbl.pack(side=tk.LEFT)

        target_dir_disp = getattr(self, "selected_output_dir", r"C:\kurtarilan_dosyalar")
        target_lbl = tk.Label(
            action_bar, 
            text=f"Hedef: {target_dir_disp}", 
            bg="#2F3542", 
            fg="#FFFFFF", 
            font=("Segoe UI", 9)
        )
        target_lbl.pack(side=tk.RIGHT)

        # Progress card
        card_frame = tk.Frame(self.scan_modal, bg="#2F3542", padx=20, pady=12, highlightthickness=1, highlightbackground="#57606F")
        card_frame.pack(fill=tk.X, padx=20, pady=(0, 10))

        pct_row = tk.Frame(card_frame, bg="#2F3542")
        pct_row.pack(fill=tk.X, pady=(0, 8))

        self.modal_pct_lbl = tk.Label(pct_row, text="%0.0", bg="#2F3542", fg="#00CEC9", font=("Segoe UI", 22, "bold"))
        self.modal_pct_lbl.pack(side=tk.LEFT)

        self.modal_gb_lbl = tk.Label(pct_row, text=f"Taranan: 0.00 GB / {drive_total_gb:.2f} GB", bg="#2F3542", fg="#FFFFFF", font=("Segoe UI", 11, "bold"))
        self.modal_gb_lbl.pack(side=tk.RIGHT)

        self.modal_progress_bar = ttk.Progressbar(card_frame, orient="horizontal", mode="determinate")
        self.modal_progress_bar.pack(fill=tk.X, pady=(0, 10))

        # Stat pills row
        pills_row = tk.Frame(card_frame, bg="#2F3542")
        pills_row.pack(fill=tk.X)

        self.modal_speed_lbl = tk.Label(pills_row, text="⚡ Hız: 0.00 MB/s", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.modal_speed_lbl.pack(side=tk.LEFT, padx=(0, 10))

        self.modal_elapsed_lbl = tk.Label(pills_row, text="⏱️ Süre: 00:00", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.modal_elapsed_lbl.pack(side=tk.LEFT, padx=(0, 10))

        self.modal_eta_lbl = tk.Label(pills_row, text="⏳ Kalan: Hesaplanıyor...", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.modal_eta_lbl.pack(side=tk.LEFT, padx=(0, 10))

        self.modal_count_lbl = tk.Label(pills_row, text="📁 Bulunan: 0 dosya (0 MB)", bg="#1E1E24", fg="#FF9F43", font=("Segoe UI", 9, "bold"), padx=10, pady=4)
        self.modal_count_lbl.pack(side=tk.LEFT)

        # Live Console Activity Feed
        log_frame = tk.LabelFrame(self.scan_modal, text=" Canlı Taranan Dosyalar ve Klasör Yapısı ", bg="#1E1E24", fg="#FFFFFF", font=("Segoe UI", 9, "bold"), padx=10, pady=8)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=20, pady=(0, 10))

        self.modal_log_text = tk.Text(log_frame, bg="#000000", fg="#00FF66", font=("Consolas", 9), borderwidth=0, highlightthickness=0, wrap="char")
        self.modal_log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        modal_scroll = ttk.Scrollbar(log_frame, orient="vertical", command=self.modal_log_text.yview)
        modal_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.modal_log_text.config(yscrollcommand=modal_scroll.set)

        self.modal_log_text.insert(tk.END, f"[*] {clean_name} tarama paneli hazır.\n")
        self.modal_log_text.insert(tk.END, "[*] Taramayı başlatmak için yukarıdaki '🚀 TARAMAYI BAŞLAT' butonuna tıklayın.\n")

        # Populate current virtual_files if already found
        if hasattr(self, "virtual_files") and self.virtual_files:
            for f in self.virtual_files[:50]:
                p_name = f.get("custom_path") or f.get("name")
                sz_str = self.format_size(f.get("size", 0))
                self.modal_log_text.insert(tk.END, f"[✔] {p_name} ({sz_str}) - Tarih: {f.get('date', '-')}\n")
            self.modal_log_text.see(tk.END)

        # Action Buttons at Bottom
        btn_frame = tk.Frame(self.scan_modal, bg="#1E1E24", padx=20, pady=10)
        btn_frame.pack(fill=tk.X, side=tk.BOTTOM)

        self.modal_inspect_btn = tk.Button(
            btn_frame, 
            text="🔎 BULUNAN DOSYALARI İNCELE & GERİ YÜKLE", 
            command=lambda: (self.scan_modal.destroy(), self.show_file_view()), 
            bg="#0084FF", 
            fg="#FFFFFF", 
            font=("Segoe UI", 10, "bold"), 
            padx=15, 
            pady=6, 
            borderwidth=0,
            cursor="hand2"
        )
        self.modal_inspect_btn.pack(side=tk.LEFT)

        close_btn = tk.Button(
            btn_frame, 
            text="✖️ KAPAT (Arka Planda Devam Et)", 
            command=self.scan_modal.destroy, 
            bg="#57606F", 
            fg="#FFFFFF", 
            font=("Segoe UI", 9, "bold"), 
            padx=12, 
            pady=6, 
            borderwidth=0,
            cursor="hand2"
        )
        close_btn.pack(side=tk.RIGHT)

        # Start modal heartbeat ticker loop
        self.modal_ticker_sec = 0
        self.update_modal_ticker_loop()

    def trigger_modal_start_recovery(self):
        if hasattr(self, "modal_start_btn"):
            self.modal_start_btn.config(state="disabled", bg="#57606F", text="⏳ TARAMA ÇALIŞIYOR...")
        if hasattr(self, "modal_log_text"):
            self.modal_log_text.insert(tk.END, "\n[🚀] Taramaya başlandı! Sektörler ve MFT indeksi taranıyor...\n")
            self.modal_log_text.see(tk.END)
        self.start_recovery()

    def update_modal_ticker_loop(self):
        if getattr(self, "scan_modal", None) and self.scan_modal.winfo_exists():
            if getattr(self, "is_scanning", False):
                self.modal_ticker_sec = getattr(self, "modal_ticker_sec", 0) + 1
                if hasattr(self, "modal_heartbeat_lbl"):
                    self.modal_heartbeat_lbl.config(text=f"🟢 Canlı Sayaç: {self.modal_ticker_sec} sn (Motor Çalışıyor ✅)")
            else:
                if hasattr(self, "modal_heartbeat_lbl"):
                    self.modal_heartbeat_lbl.config(text="🟢 Canlı Sayaç: Beklemede")
            self.after(1000, self.update_modal_ticker_loop)



    def populate_detail_map_tree(self, tree):
        selected_items = tree.selection()
        selected_blocks = set()
        for item in selected_items:
            try:
                txt = tree.item(item, "text")
                num = int(txt.replace("Blok", "").strip())
                selected_blocks.add(num)
            except:
                pass
                
        tree.delete(*tree.get_children())
        
        total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
        cols = 100
        
        scanned_intervals = []
        try:
            segment_size_gb = float(self.segment_size_gb_var.get())
            if segment_size_gb <= 0: segment_size_gb = 100.0
        except:
            segment_size_gb = 100.0
        segment_size_bytes = int(segment_size_gb * 1024 * 1024 * 1024)

        if hasattr(self, "segment_progress") and self.segment_progress:
            with self.segment_lock:
                for seg_start, prog in self.segment_progress.items():
                    seg_end = seg_start + segment_size_bytes
                    if hasattr(self, "segment_bounds") and self.segment_bounds:
                        if seg_start in self.segment_bounds:
                            seg_end = self.segment_bounds[seg_start]
                    elif hasattr(self, "scan_segments") and self.scan_segments:
                        for start, end in self.scan_segments:
                            if start == seg_start:
                                seg_end = end
                                break
                    if seg_end > total_size:
                        seg_end = total_size
                    scanned_intervals.append((seg_start, seg_start + prog, seg_end))
                    
        block_file_counts = [0] * cols
        if hasattr(self, "virtual_files") and self.virtual_files:
            for f in self.virtual_files:
                offset = f.get("offset", 0)
                if total_size > 0:
                    block_idx = int((offset / total_size) * cols)
                    if 0 <= block_idx < cols:
                        block_file_counts[block_idx] += 1
                        
        for i in range(cols):
            block_start = (i / cols) * total_size
            block_end = ((i + 1) / cols) * total_size
            block_len = block_end - block_start
            
            total_scanned_in_block = 0
            is_currently_scanning = False
            
            for seg_start, seg_scanned, seg_end in scanned_intervals:
                overlap_start = max(block_start, seg_start)
                overlap_end = min(block_end, seg_scanned)
                if overlap_end > overlap_start:
                    total_scanned_in_block += (overlap_end - overlap_start)
                
                if getattr(self, "is_scanning", False) and seg_scanned > seg_start and seg_scanned < seg_end:
                    if block_start <= seg_scanned <= block_end:
                        is_currently_scanning = True
                        
            scanned_pct = total_scanned_in_block / block_len if block_len > 0 else 0
            
            range_str = f"{block_start / (1024*1024*1024):.2f} GB - {block_end / (1024*1024*1024):.2f} GB"
            scanned_str = f"{total_scanned_in_block / (1024*1024*1024):.2f} GB (%{scanned_pct*100:.1f})"
            recovered_str = f"{block_file_counts[i]} dosya"
            
            copy_val = getattr(self, "block_copy_counts", [0]*100)[i]
            unwanted_val = getattr(self, "block_unwanted_counts", [0]*100)[i]
            copies_str = f"{copy_val} kopya"
            unwanted_str = f"{unwanted_val} öğe"
            
            if is_currently_scanning:
                status = "Taranıyor"
                tag = "scanning"
            elif (i + 1) in getattr(self, "scan_queue", []):
                status = "Kuyrukta"
                tag = "queued"
            elif scanned_pct >= 0.95:
                status = "Tarandı"
                tag = "scanned"
            elif scanned_pct > 0.05:
                status = "Kısmen Tarandı"
                tag = "partial"
            else:
                status = "Taranmadı"
                tag = "unscanned"
                
            node = tree.insert("", "end", text=f"Blok {i+1}", values=(range_str, scanned_str, recovered_str, copies_str, unwanted_str, status), tags=(tag,))
            
            if selected_blocks:
                if (i + 1) in selected_blocks:
                    tree.selection_add(node)
            elif hasattr(self, "selected_canvas_blocks") and (i + 1) in self.selected_canvas_blocks:
                tree.selection_add(node)

    def on_drive_select(self, event=None):
        import os
        selected = self.drive_var.get()
        if not selected or not hasattr(self, "drives_details_map"):
            return
            
        details = self.drives_details_map.get(selected)
        if not details:
            return
            
        # Update model label
        self.lbl_drive_model.config(text=f"Model: {details['name']}")
        
        # Update health label
        health = details['health']
        color = "#10AC84" if health.lower() == "healthy" else "#FF4757"
        self.lbl_drive_health.config(text=f"Sağlık (SMART): {health}", fg=color)
        
        # Update partition style
        self.lbl_drive_partition.config(text=f"Bölümleme Stili: {details['partition_style']}")
        
        # Update capacity
        size_gb = details['size_gb']
        if size_gb >= 1024:
            self.lbl_drive_capacity.config(text=f"Kapasite: {size_gb / 1024:.2f} TB")
        else:
            self.lbl_drive_capacity.config(text=f"Kapasite: {size_gb} GB")
            
        if hasattr(self, "lbl_drive_scanned") and self.lbl_drive_scanned:
            self.lbl_drive_scanned.config(text="Taranan Alan: 0.00 GB (%0.0)", fg=self.text_dark)
            
        # Update active drive reference
        if hasattr(self, "drives_map") and self.drives_map:
            self.active_drive = self.drives_map.get(selected)
            self.active_drive_size = self.drives_sizes_map.get(selected, 0)
            
        # Automatically update default target directory if no session is active
        if not getattr(self, "current_session_file", None):
            suggested_root = self.get_default_target_drive_root()
            if suggested_root:
                self.selected_output_dir = os.path.abspath(os.path.join(suggested_root, "kurtarilan_dosyalar"))
                self.update_target_drive_status()
                if hasattr(self, "path_lbl") and self.path_lbl:
                    self.path_lbl.config(text=self.selected_output_dir)

    def update_target_drive_status(self):
        import shutil
        import os
        
        path = getattr(self, "selected_output_dir", None)
        if not path:
            path = os.path.abspath("kurtarilan_dosyalar")
            
        try:
            drive_root = os.path.splitdrive(path)[0] + "\\"
            if not drive_root or drive_root == "\\":
                drive_root = "C:\\"
            
            total, used, free = shutil.disk_usage(drive_root)
            
            total_gb = total / (1024 * 1024 * 1024)
            used_gb = used / (1024 * 1024 * 1024)
            free_gb = free / (1024 * 1024 * 1024)
            
            pct = (used / total * 100) if total > 0 else 0
            
            if hasattr(self, "lbl_target_path") and self.lbl_target_path:
                # Wrap path if too long
                display_path = path
                if len(path) > 32:
                    display_path = path[:15] + "..." + path[-15:]
                self.lbl_target_path.config(text=f"Konum: {display_path}")
            if hasattr(self, "lbl_target_total") and self.lbl_target_total:
                self.lbl_target_total.config(text=f"Toplam Kapasite: {total_gb:.2f} GB")
            if hasattr(self, "lbl_target_used") and self.lbl_target_used:
                self.lbl_target_used.config(text=f"Kullanılan / Boş: {used_gb:.2f} GB / {free_gb:.2f} GB")
            if hasattr(self, "lbl_target_percent") and self.lbl_target_percent:
                self.lbl_target_percent.config(text=f"Doluluk Oranı: %{pct:.1f}")
            if hasattr(self, "target_usage_bar") and self.target_usage_bar:
                self.target_usage_bar.config(value=pct)
        except Exception as e:
            print(f"Error updating target drive status: {e}")


