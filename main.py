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

if __name__ == "__main__":
    run_as_admin()
    
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
