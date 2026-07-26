import threading
import subprocess
import json

def get_drive_size_win32(drive_path):
    try:
        import ctypes
        from ctypes import wintypes
        GENERIC_READ = 0x80000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3
        IOCTL_DISK_GET_LENGTH_INFO = 0x0007405C

        handle = ctypes.windll.kernel32.CreateFileW(
            drive_path, GENERIC_READ, FILE_SHARE_READ | FILE_SHARE_WRITE,
            None, OPEN_EXISTING, 0, None
        )
        if handle == -1 or handle == 0 or handle == 0xFFFFFFFF:
            return 0

        class GET_LENGTH_INFORMATION(ctypes.Structure):
            _fields_ = [("Length", ctypes.c_int64)]

        length_info = GET_LENGTH_INFORMATION()
        bytes_returned = wintypes.DWORD()
        success = ctypes.windll.kernel32.DeviceIoControl(
            handle, IOCTL_DISK_GET_LENGTH_INFO, None, 0,
            ctypes.byref(length_info), ctypes.sizeof(length_info),
            ctypes.byref(bytes_returned), None
        )
        ctypes.windll.kernel32.CloseHandle(handle)
        if success:
            return length_info.Length
    except:
        pass
    return 0

class DrivesMixin:
    def load_physical_drives(self):
        self.drive_combo.config(values=["Diskler aranıyor..."])
        self.drive_combo.current(0)
        threading.Thread(target=self._async_load_drives, daemon=True).start()

    def _async_load_drives(self):
        options = []
        local_drives_map = {}
        local_drives_sizes_map = {}
        local_drives_details_map = {}

        try:
            cmd = 'powershell -NoProfile -Command "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-Disk | Select-Object Number, FriendlyName, Size, PartitionStyle, HealthStatus | ConvertTo-Json"'
            result = subprocess.run(cmd, capture_output=True, text=True, errors="ignore", timeout=10, shell=True)
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
                    path = rf"\\.\PhysicalDrive{num}"
                    local_drives_map[display_str] = path
                    local_drives_sizes_map[display_str] = size
                    local_drives_details_map[display_str] = {
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
            for i in range(10):
                path = rf"\\.\PhysicalDrive{i}"
                size = get_drive_size_win32(path)
                if size > 0:
                    display_str = f"PhysicalDrive{i} ({int(size / (1024*1024*1024))} GB)"
                    options.append(display_str)
                    local_drives_map[display_str] = path
                    local_drives_sizes_map[display_str] = size
                    local_drives_details_map[display_str] = {
                        "name": f"PhysicalDrive{i}",
                        "size": size,
                        "size_gb": int(size / (1024 * 1024 * 1024)),
                        "partition_style": "Bilinmiyor",
                        "health": "Healthy",
                        "number": i
                    }
                    
        if not options:
            options = ["PhysicalDrive0", "PhysicalDrive1", "PhysicalDrive2"]
            local_drives_map = {opt: rf"\\.\{opt}" for opt in options}
            local_drives_sizes_map = {opt: 0 for opt in options}
            local_drives_details_map = {opt: {
                "name": opt, "size": 0, "size_gb": 0, "partition_style": "Bilinmiyor", "health": "Healthy", "number": idx
            } for idx, opt in enumerate(options)}
            
        self.msg_queue.put(("loaded_drives", {
            "options": options,
            "drives_map": local_drives_map,
            "drives_sizes_map": local_drives_sizes_map,
            "drives_details_map": local_drives_details_map
        }))
