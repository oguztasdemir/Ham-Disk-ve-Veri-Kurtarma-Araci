# main.py
import sys
import ctypes

def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    if not is_admin():
        # Relaunch the script with admin rights
        ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), None, 1
        )
        sys.exit(0)

def hide_console():
    try:
        import ctypes
        hwnd = ctypes.windll.kernel32.GetConsoleWindow()
        if hwnd:
            ctypes.windll.user32.ShowWindow(hwnd, 0)
    except:
        pass

def enforce_single_instance():
    import os
    import time
    PID_FILE = "app.pid"
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, "r") as f:
                old_pid = int(f.read().strip())
            
            # Check if the process exists and kill it
            try:
                os.kill(old_pid, 0)
                os.system(f"taskkill /F /PID {old_pid} >nul 2>&1")
                time.sleep(0.5)
            except OSError:
                pass
        except:
            pass
            
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
    except:
        pass

def check_dependencies():
    import sys
    try:
        from PIL import Image, ImageTk
    except ImportError:
        import subprocess
        try:
            print("Gerekli kütüphaneler kuruluyor (Pillow)...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            print("Kurulum başarılı!")
        except Exception as e:
            print(f"Kütüphane kurulumu sırasında hata oluştu: {e}")

if __name__ == "__main__":
    enforce_single_instance()
    run_as_admin()
    hide_console()
    check_dependencies()
    
    try:
        from ui import RecoveryApp
        app = RecoveryApp()
        app.mainloop()
    except Exception as e:
        import traceback
        error_msg = f"Program başlatılırken bir hata oluştu:\n\n{e}\n\nDetaylar:\n{traceback.format_exc()}"
        print(error_msg)
        try:
            import ctypes
            ctypes.windll.user32.MessageBoxW(0, error_msg, "Başlatma Hatası", 0x10)
        except:
            pass
        input("\nÇıkmak için Enter tuşuna basın...")
