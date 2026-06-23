import tkinter as tk
from tkinter import ttk
from config import CATEGORIES

class LayoutMixin:
    def create_widgets(self):
        # Console Log Button placed at the top-right corner of the application window
        self.log_btn = tk.Button(
            self, 
            text="📋 Konsol Akışı", 
            command=self.show_console_log_window, 
            bg="#2F3542", 
            fg=self.text_white, 
            activebackground=self.accent_blue, 
            activeforeground=self.text_white, 
            borderwidth=0, 
            padx=10, 
            pady=5, 
            font=("Segoe UI", 9, "bold")
        )
        self.log_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=10)

        # Left Sidebar
        sidebar = tk.Frame(self, bg=self.sidebar_bg, width=260)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)
        
        logo_lbl = tk.Label(sidebar, text="= Disk Drill", bg=self.sidebar_bg, fg=self.text_dark, font=("Segoe UI", 12, "bold"))
        logo_lbl.pack(anchor="w", padx=20, pady=20)
        
        self.dash_btn = tk.Button(sidebar, text="📊 Gösterge Tablosu", command=self.show_dashboard_view, bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=20, pady=10, font=("Segoe UI", 10, "bold"))
        self.dash_btn.pack(fill=tk.X)

        self.help_btn = tk.Button(sidebar, text="❓ Nasıl Çalışır / Yardım", command=self.show_help_window, bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=20, pady=10, font=("Segoe UI", 10, "bold"))
        self.help_btn.pack(fill=tk.X)
        
        tk.Label(sidebar, text="Sonuçlar", bg=self.sidebar_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold")).pack(anchor="w", padx=20, pady=(20, 5))
        
        self.sidebar_buttons = {}
        self.all_files_btn = tk.Button(sidebar, text="📁 Tüm Dosyalar", command=lambda: self.set_category_filter("All"), bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=25, pady=8, font=("Segoe UI", 9))
        self.all_files_btn.pack(fill=tk.X)
        
        for cat_name, info in CATEGORIES.items():
            btn = tk.Button(sidebar, text=f"{info['icon']} {cat_name} (0)", command=lambda c=cat_name: self.set_category_filter(c), bg=self.sidebar_bg, fg=self.text_dark, activebackground="#E4E5EA", activeforeground=self.text_dark, borderwidth=0, anchor="w", padx=25, pady=6, font=("Segoe UI", 9))
            btn.pack(fill=tk.X)
            self.sidebar_buttons[cat_name] = btn
            
        # Target Path selection at sidebar bottom
        sidebar_bottom = tk.Frame(sidebar, bg=self.sidebar_bg)
        sidebar_bottom.pack(side=tk.BOTTOM, fill=tk.X, padx=15, pady=15)
        
        tk.Label(sidebar_bottom, text="Kurtarma Konumu:", bg=self.sidebar_bg, fg=self.text_gray, font=("Segoe UI", 8, "bold")).pack(anchor="w")
        self.path_lbl = tk.Label(sidebar_bottom, text=self.selected_output_dir, bg="#E4E5EA", fg=self.text_dark, wraplength=220, justify="left", font=("Segoe UI", 8), padx=5, pady=5)
        self.path_lbl.pack(fill=tk.X, pady=5)
        
        change_path_btn = tk.Button(sidebar_bottom, text="Konumu Değiştir", command=self.select_output_directory, bg="#DCDDE1", fg=self.text_dark, borderwidth=0, pady=4, font=("Segoe UI", 8, "bold"))
        change_path_btn.pack(fill=tk.X)

        # Right Content Window
        self.content_frame = tk.Frame(self, bg=self.content_bg)
        self.content_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.dashboard_view = tk.Frame(self.content_frame, bg=self.content_bg, padx=30, pady=20)
        self.file_view = tk.Frame(self.content_frame, bg=self.content_bg)
        
        self.init_dashboard_view()
        self.init_file_view()
        self.show_dashboard_view()

    def init_dashboard_view(self):
        # Split dashboard into Left (Controls) and Right (RAM & Log Panel)
        self.dash_left_frame = tk.Frame(self.dashboard_view, bg=self.content_bg)
        self.dash_left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.dash_right_frame = tk.Frame(self.dashboard_view, bg=self.content_bg, width=280)
        self.dash_right_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        self.dash_right_frame.pack_propagate(False)
        
        # RAM usage label at top-right of dashboard view
        self.ram_lbl = tk.Label(self.dash_right_frame, text="RAM: Yükleniyor...", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold"))
        self.ram_lbl.pack(anchor="ne", pady=(0, 10))
        
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
        
        # S.M.A.R.T Diagnostics panel at the bottom of the right panel
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
        settings_bar.pack(fill=tk.X, pady=(0, 20))
        
        tk.Label(settings_bar, text="Sürücü Seçin:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 10, "bold")).pack(side=tk.LEFT, padx=(0, 10))
        self.drive_var = tk.StringVar()
        self.drive_combo = ttk.Combobox(settings_bar, textvariable=self.drive_var, state="readonly", width=30)
        self.drive_combo.pack(side=tk.LEFT, padx=(0, 10))
        self.drive_combo.bind("<<ComboboxSelected>>", self.on_drive_select)
        
        refresh_btn = tk.Button(settings_bar, text="Yenile", command=self.load_physical_drives, bg="#F1F2F6", fg=self.text_dark, borderwidth=1, relief="solid", padx=10, font=("Segoe UI", 9))
        refresh_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.start_btn = tk.Button(settings_bar, text="SANAL TARAMAYI BAŞLAT", command=self.start_recovery, bg=self.accent_blue, fg=self.text_white, borderwidth=0, padx=15, pady=5, font=("Segoe UI", 9, "bold"))
        self.start_btn.pack(side=tk.LEFT)
        
        # Parallel scan settings bar
        self.parallel_bar = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.parallel_bar.pack(fill=tk.X, pady=(0, 20))
        
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
        
        # Custom range settings bar
        self.custom_range_bar = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.custom_range_bar.pack(fill=tk.X, pady=(0, 20))
        
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
        
        self.custom_start_lbl = tk.Label(self.custom_range_bar, text="Başlangıç:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.custom_start_lbl.pack(side=tk.LEFT, padx=(0, 5))
        
        self.custom_start_entry = tk.Entry(
            self.custom_range_bar,
            textvariable=self.custom_start_var,
            state="disabled",
            width=8
        )
        self.custom_start_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        self.custom_end_lbl = tk.Label(self.custom_range_bar, text="Bitiş:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.custom_end_lbl.pack(side=tk.LEFT, padx=(0, 5))
        
        self.custom_end_entry = tk.Entry(
            self.custom_range_bar,
            textvariable=self.custom_end_var,
            state="disabled",
            width=8
        )
        self.custom_end_entry.pack(side=tk.LEFT, padx=(0, 15))
        
        self.custom_unit_lbl = tk.Label(self.custom_range_bar, text="Birim:", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.custom_unit_lbl.pack(side=tk.LEFT, padx=(0, 5))
        
        self.custom_unit_combo = ttk.Combobox(
            self.custom_range_bar,
            textvariable=self.custom_unit_var,
            values=["MB", "GB", "TB"],
            state="disabled",
            width=5
        )
        self.custom_unit_combo.pack(side=tk.LEFT)
        
        self.scan_header_lbl = tk.Label(self.dash_left_frame, text="Cihaz Seçin ve Taramayı Başlatın", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 16, "bold"))
        self.scan_header_lbl.pack(anchor="w", pady=(0, 5))
        
        self.scan_progress_lbl = tk.Label(self.dash_left_frame, text="Taramayı başlattığınızda veriler yer kaplamadan burada listelenecektir.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 10))
        self.scan_progress_lbl.pack(anchor="w", pady=(0, 20))
        
        self.cards_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.cards_frame.pack(fill=tk.X, pady=10)
        
        self.card_widgets = {}
        categories_list = list(CATEGORIES.keys())
        for idx, name in enumerate(categories_list):
            info = CATEGORIES[name]
            r = idx // 3
            c = idx % 3
            
            card = tk.Frame(self.cards_frame, bg=info["color"], width=280, height=130, bd=0, padx=15, pady=15)
            card.grid(row=r, column=c, padx=10, pady=10)
            card.grid_propagate(False)
            
            icon_lbl = tk.Label(card, text=info["icon"], bg=info["color"], fg=self.text_white, font=("Segoe UI", 24))
            icon_lbl.pack(anchor="nw")
            
            title_lbl = tk.Label(card, text=name, bg=info["color"], fg=self.text_white, font=("Segoe UI", 11, "bold"))
            title_lbl.pack(anchor="sw", pady=(15, 0))
            
            count_lbl = tk.Label(card, text="0 Dosya Bulundu", bg=info["color"], fg=self.text_white, font=("Segoe UI", 9))
            count_lbl.pack(anchor="sw")
            
            # Make the entire card interactive and clickable
            for widget in (card, icon_lbl, title_lbl, count_lbl):
                widget.bind("<Button-1>", lambda event, cat_name=name: self.set_category_filter(cat_name))
                widget.config(cursor="hand2")
                
            self.card_widgets[name] = {"count_lbl": count_lbl, "frame": card}
            
        # Disk Visual Map Frame
        self.disk_map_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.disk_map_frame.pack(fill=tk.X, pady=(10, 0))
        
        map_title_row = tk.Frame(self.disk_map_frame, bg=self.content_bg)
        map_title_row.pack(fill=tk.X, pady=(0, 5))
        
        tk.Label(map_title_row, text="Diskin Görsel Durum Haritası (100 Blok)", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT)
        
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
        
        self.disk_map_canvas = tk.Canvas(self.disk_map_frame, bg="#1E272E", height=60, highlightthickness=1, highlightbackground="#57606F")
        self.disk_map_canvas.pack(fill=tk.X)
            
        ctrl_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        ctrl_frame.pack(fill=tk.X, pady=20)
        
        self.pause_btn = tk.Button(ctrl_frame, text="DURAKLAT", command=self.pause_recovery, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, padx=15, pady=8, font=("Segoe UI", 9, "bold"))
        self.pause_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.resume_btn = tk.Button(ctrl_frame, text="DEVAM ET", command=self.resume_recovery, state="disabled", bg="#CED6E0", fg=self.text_dark, borderwidth=0, padx=15, pady=8, font=("Segoe UI", 9, "bold"))
        self.resume_btn.pack(side=tk.LEFT, padx=(0, 10))
        
        self.stop_btn = tk.Button(ctrl_frame, text="TARAMAYI BİTİR", command=self.stop_recovery, state="disabled", bg="#FF4757", fg=self.text_white, borderwidth=0, padx=15, pady=8, font=("Segoe UI", 9, "bold"))
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 20))
        
        self.inspect_btn = tk.Button(ctrl_frame, text="🔎 Bulunan Öğeleri İnceleyin", command=self.show_file_view, bg=self.accent_blue, fg=self.text_white, borderwidth=0, padx=20, pady=8, font=("Segoe UI", 9, "bold"))
        self.inspect_btn.pack(side=tk.RIGHT)
        
        self.status_lbl = tk.Label(self.dash_left_frame, text="Hazır.", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9))
        self.status_lbl.pack(side=tk.BOTTOM, anchor="w")
 
        self.progress_bar = ttk.Progressbar(self.dash_left_frame, orient="horizontal", mode="determinate")
        self.progress_bar.pack(fill=tk.X, side=tk.BOTTOM, pady=10)
 
        # Stats Grid for comprehensive metadata
        self.stats_frame = tk.Frame(self.dash_left_frame, bg=self.content_bg)
        self.stats_frame.pack(fill=tk.X, side=tk.BOTTOM, pady=(0, 5))
        
        self.lbl_progress_title = tk.Label(self.stats_frame, text="İlerleme:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_progress_title.grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.lbl_progress_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.lbl_progress_val.grid(row=0, column=1, sticky="w", padx=(0, 30), pady=2)
        
        self.lbl_speed_title = tk.Label(self.stats_frame, text="Tarama Hızı:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_speed_title.grid(row=0, column=2, sticky="w", padx=(0, 10), pady=2)
        self.lbl_speed_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.lbl_speed_val.grid(row=0, column=3, sticky="w", padx=(0, 30), pady=2)
        
        self.lbl_elapsed_title = tk.Label(self.stats_frame, text="Geçen Süre:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_elapsed_title.grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        self.lbl_elapsed_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.lbl_elapsed_val.grid(row=1, column=1, sticky="w", padx=(0, 30), pady=2)
        
        self.lbl_eta_title = tk.Label(self.stats_frame, text="Tahmini Kalan Süre:", bg=self.content_bg, fg=self.text_gray, font=("Segoe UI", 9, "bold"))
        self.lbl_eta_title.grid(row=1, column=2, sticky="w", padx=(0, 10), pady=2)
        self.lbl_eta_val = tk.Label(self.stats_frame, text="-", bg=self.content_bg, fg=self.text_dark, font=("Segoe UI", 9))
        self.lbl_eta_val.grid(row=1, column=3, sticky="w", padx=(0, 30), pady=2)

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
        
        vid_icon = tk.Label(vid_container, text="🎬", bg="#F1F2F6", fg=self.accent_blue, font=("Segoe UI", 48))
        vid_icon.pack(pady=10)
        
        self.vid_info_lbl = tk.Label(vid_container, text="Video Yükleniyor...", bg="#F1F2F6", fg=self.text_dark, font=("Segoe UI", 10, "bold"), justify="center", wraplength=260)
        self.vid_info_lbl.pack(pady=10)
        
        self.vid_play_btn = tk.Button(vid_container, text="▶ Pencerede Başlat (Oynat)", command=self.start_video_preview, bg=self.accent_blue, fg=self.text_white, borderwidth=0, padx=15, pady=10, font=("Segoe UI", 10, "bold"))
        self.vid_play_btn.pack(fill=tk.X, pady=5)
        
        self.vid_stop_btn = tk.Button(vid_container, text="⏹ Oynatmayı Durdur", command=self.stop_video_preview, bg="#FF4757", fg=self.text_white, borderwidth=0, padx=15, pady=10, font=("Segoe UI", 10, "bold"))
        self.vid_stop_btn.pack(fill=tk.X, pady=5)
        
        self.vid_status_lbl = tk.Label(vid_container, text="Oynatmaya hazır.", bg="#F1F2F6", fg=self.text_gray, font=("Segoe UI", 9, "italic"))
        self.vid_status_lbl.pack(pady=10)
        
        self.current_video_meta = None

    def show_dashboard_view(self):
        self.file_view.pack_forget()
        self.dashboard_view.pack(fill=tk.BOTH, expand=True)
        self.draw_disk_map()

    def show_file_view(self):
        self.dashboard_view.pack_forget()
        self.file_view.pack(fill=tk.BOTH, expand=True)
        
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
        
        title_lbl = tk.Label(header_frame, text="🛠️ Disk Drill - Profesyonel Veri Kurtarma Kılavuzu", bg="#0084FF", fg="#FFFFFF", font=("Segoe UI", 14, "bold"))
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
            "💡 Disk Drill Çözümü (Sanal Klasörleme):\n"
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
        
        close_btn = tk.Button(help_win, text="Kapat", command=help_win.destroy, bg="#2F3542", fg="#FFFFFF", borderwidth=0, padx=20, pady=8, font=("Segoe UI", 9, "bold"))
        close_btn.pack(pady=10)

    def select_output_directory(self):
        import os
        from tkinter import filedialog
        directory = filedialog.askdirectory(initialdir=self.selected_output_dir, title="Kurtarılan Dosyaları Nereye Kaydedelim?")
        if directory:
            self.selected_output_dir = os.path.abspath(directory)
            self.path_lbl.config(text=self.selected_output_dir)

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

    def update_ram_usage(self):
        import ctypes
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
            total = stat.ullTotalPhys
            avail = stat.ullAvailPhys
            used = total - avail
            total_gb = total / (1024 * 1024 * 1024)
            used_gb = used / (1024 * 1024 * 1024)
            pct = stat.dwMemoryLoad
            ram_str = f"RAM: {used_gb:.2f} GB / {total_gb:.2f} GB ({pct}%)"
        except:
            ram_str = "RAM: Bilinmiyor"
            
        if hasattr(self, "ram_lbl") and self.ram_lbl:
            self.ram_lbl.config(text=ram_str)
            
        self.after(1000, self.update_ram_usage)

    def toggle_parallel_options(self):
        state = "normal" if self.use_parallel_var.get() else "disabled"
        self.worker_combo.config(state=state if state == "disabled" else "readonly")
        self.segment_entry.config(state=state)
        
        range_state = "normal" if self.use_custom_range_var.get() else "disabled"
        self.custom_start_entry.config(state=range_state)
        self.custom_end_entry.config(state=range_state)
        self.custom_unit_combo.config(state=range_state if range_state == "disabled" else "readonly")

    def draw_disk_map(self):
        if not hasattr(self, "disk_map_canvas") or not self.disk_map_canvas:
            return
            
        canvas_w = self.disk_map_canvas.winfo_width()
        canvas_h = self.disk_map_canvas.winfo_height()
        if canvas_w < 10: canvas_w = 600
        if canvas_h < 10: canvas_h = 60
        
        self.disk_map_canvas.delete("all")
        
        total_size = self.active_drive_size if self.active_drive_size > 0 else 1.8 * 1024 * 1024 * 1024 * 1024
        
        cols = 20
        rows = 5
        total_blocks = cols * rows
        
        pad_x = 3
        pad_y = 3
        block_w = (canvas_w - (cols + 1) * pad_x) / cols
        block_h = (canvas_h - (rows + 1) * pad_y) / rows
        
        scanned_intervals = []
        if hasattr(self, "segment_progress") and self.segment_progress:
            with self.segment_lock:
                for seg_start, prog in self.segment_progress.items():
                    seg_end = seg_start + 100 * 1024 * 1024 * 1024
                    if hasattr(self, "scan_segments") and self.scan_segments:
                        for start, end in self.scan_segments:
                            if start == seg_start:
                                seg_end = end
                                break
                    scanned_intervals.append((seg_start, seg_start + prog, seg_end))
                    
        for r in range(rows):
            for c in range(cols):
                i = r * cols + c
                
                block_start = (i / total_blocks) * total_size
                block_end = ((i + 1) / total_blocks) * total_size
                
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
                    color = "#FF9F43"  # Scanning (Orange)
                elif scanned_pct >= 0.95:
                    color = "#10AC84"  # Scanned (Emerald Green)
                elif scanned_pct > 0.05:
                    color = "#2ECC71"  # Partially scanned (Green)
                else:
                    color = "#2F3542"  # Unscanned (Dark Blue/Gray)
                    
                x1 = pad_x + c * (block_w + pad_x)
                y1 = pad_y + r * (block_h + pad_y)
                x2 = x1 + block_w
                y2 = y1 + block_h
                
                self.disk_map_canvas.create_rectangle(
                    x1, y1, x2, y2,
                    fill=color,
                    outline="#57606F" if color == "#2F3542" else color,
                    width=1
                )

    def on_drive_select(self, event=None):
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


