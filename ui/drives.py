import threading
import subprocess
import json

class DrivesMixin:
    def load_physical_drives(self):
        self.drive_combo.config(values=["Diskler aranıyor..."])
        self.drive_combo.current(0)
        self.drives_map = {}
        self.drives_sizes_map = {}
        self.drives_details_map = {}
        threading.Thread(target=self._async_load_drives, daemon=True).start()

    def _async_load_drives(self):
        options = []
        try:
            cmd = 'powershell -Command "Get-Disk | Select-Object Number, FriendlyName, Size, PartitionStyle, HealthStatus | ConvertTo-Json"'
            result = subprocess.run(cmd, capture_output=True, text=True, shell=True)
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                if isinstance(data, dict):
                    data = [data]
                
                for disk in data:
                    num = disk.get("Number")
                    name = disk.get("FriendlyName", "Bilinmeyen Sürücü")
                    size = disk.get("Size", 0)
                    part_style = disk.get("PartitionStyle", "Bilinmeyen")
                    health = disk.get("HealthStatus", "Bilinmeyen")
                    
                    size_gb = int(size / (1024 * 1024 * 1024)) if size else 0
                    display_str = f"Disk {num}: {name} ({size_gb} GB)"
                    options.append(display_str)
                    self.drives_map[display_str] = rf"\\.\PhysicalDrive{num}"
                    self.drives_sizes_map[display_str] = size
                    self.drives_details_map[display_str] = {
                        "name": name,
                        "size": size,
                        "size_gb": size_gb,
                        "partition_style": part_style,
                        "health": health,
                        "number": num
                    }
        except Exception as e:
            print(f"Sürücü listeleme hatası: {e}")

        if not options:
            for i in range(5):
                path = rf"\\.\PhysicalDrive{i}"
                try:
                    with open(path, "rb") as f:
                        display_str = f"PhysicalDrive{i} (Bağlı)"
                        options.append(display_str)
                        self.drives_map[display_str] = path
                        try:
                            f.seek(0, 2)
                            size = f.tell()
                        except:
                            size = 0
                        self.drives_sizes_map[display_str] = size
                        self.drives_details_map[display_str] = {
                            "name": f"PhysicalDrive{i}",
                            "size": size,
                            "size_gb": int(size / (1024 * 1024 * 1024)) if size else 0,
                            "partition_style": "Bilinmiyor",
                            "health": "Healthy",
                            "number": i
                        }
                except:
                    pass
                    
        if not options:
            options = ["PhysicalDrive0", "PhysicalDrive1", "PhysicalDrive2"]
            self.drives_map = {opt: rf"\\.\{opt}" for opt in options}
            self.drives_sizes_map = {opt: 0 for opt in options}
            self.drives_details_map = {opt: {
                "name": opt, "size": 0, "size_gb": 0, "partition_style": "Bilinmiyor", "health": "Healthy", "number": idx
            } for idx, opt in enumerate(options)}
            
        self.msg_queue.put(("loaded_drives", options))
