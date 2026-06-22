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
        self.status_lbl.config(text="Dosyalar bilgisayara yazılıyor...")
        
        threading.Thread(target=self._save_worker, args=(files_list,), daemon=True).start()

    def _save_worker(self, files_list):
        exported_count = 0
        try:
            for f in files_list:
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
                
                out_path = os.path.join(category_dir, f["name"])
                with open(out_path, "wb") as out:
                    out.write(file_bytes)
                    
                exported_count += 1
                self.msg_queue.put(("status", f"Kaydediliyor: {exported_count}/{len(files_list)}..."))
                
            self.msg_queue.put(("finished", f"Dışa aktarma bitti! {exported_count} dosya klasörlerine ayrıldı."))
        except Exception as e:
            self.msg_queue.put(("error", f"Kaydetme sırasında bir hata oluştu: {e}"))
            self.msg_queue.put(("finished", "Dışa aktarma yarıda kesildi."))
