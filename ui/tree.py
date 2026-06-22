import re
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
        self.tree_categories_map.clear()
        self.tree_size_groups_map.clear()
        self.tree_reconstructed_node = None
        
        hide = self.hide_non_previewable.get()
        sort_opt = self.sort_var.get()
        cat_filter = self.selected_category_filter
        
        filtered_files = []
        for f in self.virtual_files:
            if cat_filter != "All" and f["category"] != cat_filter:
                continue
            if hide:
                if self.get_preview_status(f) != "Önizlenebildi":
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

        # Group files: Category -> Size Bracket -> Files list
        groups = {}
        for f in filtered_files:
            cat = f["category"]
            size_group = self.get_size_group_name(f["size"])
            groups.setdefault(cat, {}).setdefault(size_group, []).append(f)
            
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
        
        # Insert Category nodes under root reconstructed node
        for cat, size_groups in groups.items():
            cat_total = sum(len(lst) for lst in size_groups.values())
            cat_bytes = sum(sum(x["size"] for x in lst) for lst in size_groups.values())
            cat_size_str = self.format_size(cat_bytes)
            
            cat_node = self.file_tree.insert(
                self.tree_reconstructed_node, "end", 
                text=f"📁 {cat} ({cat_total})", 
                values=("-", "-", "-", "Klasör", cat_size_str, "-"),
                open=True
            )
            self.tree_categories_map[cat] = cat_node
            
            for size_group, files_list in size_groups.items():
                group_bytes = sum(x["size"] for x in files_list)
                group_size_str = self.format_size(group_bytes)
                
                size_node = self.file_tree.insert(
                    cat_node, "end", 
                    text=f"📂 {size_group} ({len(files_list)})", 
                    values=("-", "-", "-", "Klasör", group_size_str, "-"),
                    open=True
                )
                self.tree_size_groups_map[(cat, size_group)] = size_node
                
                for f in files_list:
                    size_str = self.format_size(f["size"])
                    
                    file_node = self.file_tree.insert(
                        size_node, 
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
                
        cat = f["category"]
        size_group = self.get_size_group_name(f["size"])
        
        # Filter files list in memory to recalculate size/counts
        filtered_files = []
        for x in self.virtual_files:
            if cat_filter != "All" and x["category"] != cat_filter:
                continue
            if hide:
                if self.get_preview_status(x) != "Önizlenebildi":
                    continue
            filtered_files.append(x)
            
        total_files = len(filtered_files)
        total_bytes = sum(x["size"] for x in filtered_files)
        total_size_str = self.format_size(total_bytes)
        
        # Save current open states before any insert/update
        root_was_open = True
        if self.tree_reconstructed_node:
            root_was_open = self.file_tree.item(self.tree_reconstructed_node, "open")
            
        cat_was_open = True
        if cat in self.tree_categories_map:
            cat_was_open = self.file_tree.item(self.tree_categories_map[cat], "open")
            
        map_key = (cat, size_group)
        group_was_open = True
        if map_key in self.tree_size_groups_map:
            group_was_open = self.file_tree.item(self.tree_size_groups_map[map_key], "open")
            
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
        
        # 1. Category Node
        cat_files = [x for x in filtered_files if x["category"] == cat]
        cat_total = len(cat_files)
        cat_bytes = sum(x["size"] for x in cat_files)
        cat_size_str = self.format_size(cat_bytes)
        
        if cat not in self.tree_categories_map:
            cat_node = self.file_tree.insert(
                self.tree_reconstructed_node, "end", 
                text=f"📁 {cat} ({cat_total})", 
                values=("-", "-", "-", "Klasör", cat_size_str, "-"),
                open=True
            )
            self.tree_categories_map[cat] = cat_node
        else:
            cat_node = self.tree_categories_map[cat]
            self.file_tree.item(
                cat_node, 
                text=f"📁 {cat} ({cat_total})",
                values=("-", "-", "-", "Klasör", cat_size_str, "-")
            )
            
        # 2. Size Group Node
        group_files = [x for x in cat_files if self.get_size_group_name(x["size"]) == size_group]
        group_total = len(group_files)
        group_bytes = sum(x["size"] for x in group_files)
        group_size_str = self.format_size(group_bytes)
        
        if map_key not in self.tree_size_groups_map:
            size_node = self.file_tree.insert(
                cat_node, "end", 
                text=f"📂 {size_group} ({group_total})", 
                values=("-", "-", "-", "Klasör", group_size_str, "-"),
                open=True
            )
            self.tree_size_groups_map[map_key] = size_node
        else:
            size_node = self.tree_size_groups_map[map_key]
            self.file_tree.item(
                size_node, 
                text=f"📂 {size_group} ({group_total})",
                values=("-", "-", "-", "Klasör", group_size_str, "-")
            )
            
        # 3. File Node
        size_str = self.format_size(f["size"])
        
        file_node = self.file_tree.insert(
            size_node, 
            "end", 
            text=f["name"], 
            values=("Yüksek", "-", self.get_preview_status(f), f"{f['type_name']} Dosyası", size_str, f"Ofset {f['offset']}")
        )
        self.tree_item_map[file_node] = f
        
        # Restore open/collapse states if any parent was collapsed
        if not root_was_open:
            self.file_tree.item(self.tree_reconstructed_node, open=False)
        if not cat_was_open:
            self.file_tree.item(cat_node, open=False)
        if not group_was_open:
            self.file_tree.item(size_node, open=False)

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
