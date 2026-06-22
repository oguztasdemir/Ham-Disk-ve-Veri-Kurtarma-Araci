import re
from tkinter import messagebox
from config import CATEGORIES

class TreeMixin:
    def get_selected_virtual_files(self):
        selection = self.file_tree.selection()
        if not selection:
            return []
            
        selected_files = []
        
        def collect_files(node_id):
            if node_id in self.tree_item_map:
                selected_files.append(self.tree_item_map[node_id])
            else:
                for child in self.file_tree.get_children(node_id):
                    collect_files(child)
                    
        for node in selection:
            collect_files(node)
            
        return selected_files

    def update_file_listbox_view(self):
        # Clear existing Treeview items
        self.file_tree.delete(*self.file_tree.get_children())
        self.tree_item_map.clear()
        
        # Initialize folder nodes and stats
        self.folder_nodes = {}
        self.folder_stats = {}
        self.tree_reconstructed_node = None
        
        hide = self.hide_non_previewable.get()
        sort_opt = self.sort_var.get()
        cat_filter = self.selected_category_filter
        
        search_query = getattr(self, "search_var", None)
        search_query_val = search_query.get().lower().strip() if search_query else ""
        
        filtered_files = []
        for f in self.virtual_files:
            if cat_filter != "All" and f["category"] != cat_filter:
                continue
            if hide:
                if self.get_preview_status(f) != "Önizlenebildi":
                    continue
            if search_query_val and search_query_val not in f["name"].lower():
                continue
            filtered_files.append(f)
            
        def natural_sort_key(s):
            return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

        # Determine sort configuration
        sort_col = getattr(self, "sort_column", None)
        sort_desc = getattr(self, "sort_descending", False)
        
        if sort_col == "#0":
            filtered_files.sort(key=lambda x: natural_sort_key(x["name"]), reverse=sort_desc)
        elif sort_col == "size":
            filtered_files.sort(key=lambda x: x["size"], reverse=sort_desc)
        elif sort_col == "offset":
            filtered_files.sort(key=lambda x: x["offset"], reverse=sort_desc)
        elif sort_col == "chance":
            filtered_files.sort(key=lambda x: (x["category"], x["name"]), reverse=sort_desc)
        elif sort_col == "preview":
            filtered_files.sort(key=lambda x: self.get_preview_status(x), reverse=sort_desc)
        elif sort_col == "type":
            filtered_files.sort(key=lambda x: x["type_name"].lower(), reverse=sort_desc)
        else:
            # Fallback to combobox options
            if sort_opt == "İsim (A-Z)":
                filtered_files.sort(key=lambda x: natural_sort_key(x["name"]))
            elif sort_opt == "İsim (Z-A)":
                filtered_files.sort(key=lambda x: natural_sort_key(x["name"]), reverse=True)
            elif sort_opt == "Boyut (Büyükten Küçüğe)":
                filtered_files.sort(key=lambda x: x["size"], reverse=True)
            elif sort_opt == "Boyut (Küçükten Büyüye)":
                filtered_files.sort(key=lambda x: x["size"])

        total_files = len(filtered_files)
        total_bytes = sum(f["size"] for f in filtered_files)
        total_size_str = self.format_size(total_bytes)
        
        # Create Root reconstructed node
        self.tree_reconstructed_node = self.file_tree.insert(
            "", "end", 
            text=f"Yeniden inşa edildi ({total_files}) - {total_size_str}", 
            values=("-", "-", "-", "Klasör", total_size_str, "-"),
            open=True
        )
        
        # Calculate stats for all folders and their ancestors
        for f in filtered_files:
            if f.get("custom_path"):
                path_components = [p.strip() for p in re.split(r'[/\\]', f["custom_path"]) if p.strip()]
            else:
                path_components = [f["category"], self.get_size_group_name(f["size"])]
            
            for i in range(1, len(path_components) + 1):
                ancestor = tuple(path_components[:i])
                stats = self.folder_stats.setdefault(ancestor, {"count": 0, "size": 0})
                stats["count"] += 1
                stats["size"] += f["size"]
                
        def get_or_create_folder_node(path_tuple):
            if not path_tuple:
                return self.tree_reconstructed_node
            if path_tuple in self.folder_nodes:
                return self.folder_nodes[path_tuple]
            
            parent_tuple = path_tuple[:-1]
            parent_node = get_or_create_folder_node(parent_tuple)
            
            folder_name = path_tuple[-1]
            stats = self.folder_stats[path_tuple]
            f_size_str = self.format_size(stats["size"])
            node_id = self.file_tree.insert(
                parent_node, "end",
                text=f"📁 {folder_name} ({stats['count']})",
                values=("-", "-", "-", "Klasör", f_size_str, "-"),
                open=True
            )
            self.folder_nodes[path_tuple] = node_id
            return node_id

        # Insert files
        for f in filtered_files:
            if f.get("custom_path"):
                path_components = [p.strip() for p in re.split(r'[/\\]', f["custom_path"]) if p.strip()]
            else:
                path_components = [f["category"], self.get_size_group_name(f["size"])]
                
            parent_node = get_or_create_folder_node(tuple(path_components))
            size_str = self.format_size(f["size"])
            
            file_node = self.file_tree.insert(
                parent_node, 
                "end", 
                text=f["name"], 
                values=("Yüksek", "-", self.get_preview_status(f), f"{f['type_name']} Dosyası", size_str, f"Ofset {f['offset']}")
            )
            self.tree_item_map[file_node] = f

    def get_size_group_name(self, size_bytes):
        if size_bytes < 100 * 1024:
            return "Küçük (100KB altı)"
        elif size_bytes < 1024 * 1024:
            return "Orta (100KB - 1MB)"
        elif size_bytes < 10 * 1024 * 1024:
            return "Büyük (1MB - 10MB)"
        else:
            return "Çok Büyük (10MB üstü)"

    def add_file_to_tree_view(self, f):
        hide = self.hide_non_previewable.get()
        cat_filter = self.selected_category_filter
        
        if cat_filter != "All" and f["category"] != cat_filter:
            return
        if hide:
            if self.get_preview_status(f) != "Önizlenebildi":
                return
                
        if f.get("custom_path"):
            path_components = [p.strip() for p in re.split(r'[/\\]', f["custom_path"]) if p.strip()]
        else:
            path_components = [f["category"], self.get_size_group_name(f["size"])]
            
        if not hasattr(self, "folder_nodes") or self.folder_nodes is None:
            self.folder_nodes = {}
        if not hasattr(self, "folder_stats") or self.folder_stats is None:
            self.folder_stats = {}
            
        if not self.tree_reconstructed_node:
            self.folder_nodes.clear()
            self.folder_stats.clear()
            
        if not hide:
            if cat_filter == "All":
                total_files = self.total_recovered_count
                total_bytes = self.total_recovered_size
            else:
                total_files = self.category_counts.get(cat_filter, 0)
                total_bytes = self.category_sizes.get(cat_filter, 0)
            total_size_str = self.format_size(total_bytes)
        else:
            filtered_files = []
            for x in self.virtual_files:
                if cat_filter != "All" and x["category"] != cat_filter:
                    continue
                if self.get_preview_status(x) != "Önizlenebildi":
                    continue
                filtered_files.append(x)
            total_files = len(filtered_files)
            total_bytes = sum(x["size"] for x in filtered_files)
            total_size_str = self.format_size(total_bytes)
            
        # 0. Check or create Root Reconstructed Node
        if not self.tree_reconstructed_node:
            self.tree_reconstructed_node = self.file_tree.insert(
                "", "end", 
                text=f"Yeniden inşa edildi ({total_files}) - {total_size_str}", 
                values=("-", "-", "-", "Klasör", total_size_str, "-"),
                open=True
            )
        else:
            self.file_tree.item(
                self.tree_reconstructed_node, 
                text=f"Yeniden inşa edildi ({total_files}) - {total_size_str}",
                values=("-", "-", "-", "Klasör", total_size_str, "-")
            )
            
        # Recursive update/create folder nodes and stats
        def get_or_create_folder_node(path_tuple):
            if not path_tuple:
                return self.tree_reconstructed_node
            
            parent_tuple = path_tuple[:-1]
            parent_node = get_or_create_folder_node(parent_tuple)
            
            stats = self.folder_stats.setdefault(path_tuple, {"count": 0, "size": 0})
            stats["count"] += 1
            stats["size"] += f["size"]
            
            folder_name = path_tuple[-1]
            f_size_str = self.format_size(stats["size"])
            
            if path_tuple not in self.folder_nodes:
                node_id = self.file_tree.insert(
                    parent_node, "end",
                    text=f"📁 {folder_name} ({stats['count']})",
                    values=("-", "-", "-", "Klasör", f_size_str, "-"),
                    open=True
                )
                self.folder_nodes[path_tuple] = node_id
            else:
                node_id = self.folder_nodes[path_tuple]
                self.file_tree.item(
                    node_id,
                    text=f"📁 {folder_name} ({stats['count']})",
                    values=("-", "-", "-", "Klasör", f_size_str, "-")
                )
            return node_id
            
        parent_node = get_or_create_folder_node(tuple(path_components))
        
        # 3. File Node
        size_str = self.format_size(f["size"])
        
        file_node = self.file_tree.insert(
            parent_node, 
            "end", 
            text=f["name"], 
            values=("Yüksek", "-", self.get_preview_status(f), f"{f['type_name']} Dosyası", size_str, f"Ofset {f['offset']}")
        )
        self.tree_item_map[file_node] = f

    def move_selected_to_folder(self):
        selected_files = self.get_selected_virtual_files()
        if not selected_files:
            messagebox.showwarning("Uyarı", "Lütfen taşımak istediğiniz dosya veya klasörleri seçin!")
            return
            
        from tkinter import simpledialog
        folder_path = simpledialog.askstring(
            "Klasöre Taşı",
            "Taşınacak hedef klasör adını girin (Örn: Resimler/Tatil):\n(Boş bırakırsanız varsayılan kategoriye geri taşınır)",
            parent=self
        )
        if folder_path is None:  # User canceled
            return
            
        folder_path = folder_path.strip()
        
        # Update custom_path for each selected virtual file
        for f in selected_files:
            if folder_path == "":
                if "custom_path" in f:
                    del f["custom_path"]
            else:
                f["custom_path"] = folder_path
                
        # Re-render the treeview to show new structure
        self.update_file_listbox_view()
        
        # Save state so that it persists
        self.save_scan_state()

    def sort_by_column(self, col):
        # Toggle or set sort direction
        if self.sort_column == col:
            self.sort_descending = not self.sort_descending
        else:
            self.sort_column = col
            if col in ["size", "offset"]:
                self.sort_descending = True
            else:
                self.sort_descending = False
                
        # Update headings to show sort indicator arrows
        cols_map = {
            "#0": "İsim",
            "chance": "Kurtarma İhtimali",
            "date": "Değiştirilme Tarihi",
            "preview": "Önizleme",
            "type": "Tür",
            "size": "Boyut",
            "offset": "Disk Ofseti"
        }
        for k, name in cols_map.items():
            arrow = ""
            if k == col:
                arrow = "  ▼" if self.sort_descending else "  ▲"
            self.file_tree.heading(k, text=name + arrow)
            
        # Update combobox display to reflect click
        if col == "#0":
            self.sort_var.set("İsim (A-Z)" if not self.sort_descending else "İsim (Z-A)")
        elif col == "size":
            self.sort_var.set("Boyut (Büyükten Küçüğe)" if self.sort_descending else "Boyut (Küçükten Büyüye)")
        else:
            dir_str = "Azalan" if self.sort_descending else "Artan"
            self.sort_var.set(f"{cols_map[col]} ({dir_str})")
            
        self.update_file_listbox_view()

    def on_sort_combo_change(self):
        val = self.sort_var.get()
        if val == "İsim (A-Z)":
            self.sort_column = "#0"
            self.sort_descending = False
        elif val == "İsim (Z-A)":
            self.sort_column = "#0"
            self.sort_descending = True
        elif val == "Boyut (Büyükten Küçüğe)":
            self.sort_column = "size"
            self.sort_descending = True
        elif val == "Boyut (Küçükten Büyüye)":
            self.sort_column = "size"
            self.sort_descending = False
        else:
            self.sort_column = None
            self.sort_descending = False
            
        # Reset heading arrows
        cols_map = {
            "#0": "İsim",
            "chance": "Kurtarma İhtimali",
            "date": "Değiştirilme Tarihi",
            "preview": "Önizleme",
            "type": "Tür",
            "size": "Boyut",
            "offset": "Disk Ofseti"
        }
        for k, name in cols_map.items():
            arrow = ""
            if k == self.sort_column:
                arrow = "  ▼" if self.sort_descending else "  ▲"
            self.file_tree.heading(k, text=name + arrow)
            
        self.update_file_listbox_view()
