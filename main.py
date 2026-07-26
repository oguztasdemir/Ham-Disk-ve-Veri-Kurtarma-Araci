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
        import os
        script_dir = os.path.dirname(os.path.abspath(__file__))
        # Relaunch the script with admin rights
        ret = ctypes.windll.shell32.ShellExecuteW(
            None, "runas", sys.executable, " ".join([f'"{arg}"' for arg in sys.argv]), script_dir, 1
        )
        if ret <= 32:
            try:
                ctypes.windll.user32.MessageBoxW(
                    0, 
                    "Ham sektör okuma ve disk kurtarma işlemleri için yönetici yetkileri gereklidir.\nLütfen uygulamayı yönetici olarak çalıştırın.", 
                    "Yönetici Yetkisi Gerekli", 
                    0x30
                )
            except:
                pass
            sys.exit(1)
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
            
            if old_pid != os.getpid():
                # Check if process is running and belongs to python.exe/main.py before terminating
                import subprocess
                try:
                    out = subprocess.check_output(f'tasklist /FI "PID eq {old_pid}"', shell=True, text=True, errors="ignore")
                    if "python" in out.lower() or "main" in out.lower():
                        subprocess.run(f"taskkill /F /PID {old_pid} >nul 2>&1", shell=True)
                        time.sleep(0.3)
                except:
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
    # Check Pillow
    try:
        from PIL import Image, ImageTk
    except ImportError:
        import subprocess
        try:
            print("Gerekli kütüphaneler kuruluyor (Pillow)...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "Pillow"])
            print("Pillow kurulumu başarılı!")
        except Exception as e:
            print(f"Pillow kurulumu sırasında hata oluştu: {e}")

    # Check moviepy
    try:
        import moviepy
    except ImportError:
        import subprocess
        try:
            print("Gerekli kütüphaneler kuruluyor (moviepy)...")
            subprocess.check_call([sys.executable, "-m", "pip", "install", "moviepy"])
            print("moviepy kurulumu başarılı!")
        except Exception as e:
            print(f"moviepy kurulumu sırasında hata oluştu: {e}")

if __name__ == "__main__":
    import os
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    run_as_admin()
    enforce_single_instance()
    check_dependencies()
    hide_console()
    
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
