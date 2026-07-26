# 🔍 NovaRecovery (Disk Kurtarma) - Kod İncelemesi, Bug ve Geliştirme Raporu

**Tarih:** 23 Temmuz 2026  
**Proje:** NovaRecovery v2.1.0 (Disk Drill Raw Recovery Style)  
**İnceleyen:** Antigravity AI  

---

## 📌 Executive Summary (Özet)

Bu rapor, `Disk Kurtarma` projesinin klasör yapısını, kaynak kodlarını (`main.py`, `config.py`, `ntfs.py`, `carver.py` ve `ui/` dizini altındaki tüm Python modüllerini) başından sonuna kadar detaylı inceleyerek hazırlanmıştır.

Yapılan inceleme sonucunda; **uygulamada kritik çalışmama risklerine, veri kaybına/bozulmasına yol açabilecek bug'lar**, **iş parçacığı (threading) ve bellek (RAM) güvenliği sorunları** ile **kod mimarisinde geliştirilmesi gereken alanlar** tespit edilmiştir.

---

## 📁 1. Klasör Yapısı ve Modül Haritası

Proje modüler bir yapıya bölünmeye çalışılmış olup dizin mimarisi şu şekildedir:

```text
Disk Kurtarma/
├── main.py                 # Başlatıcı, UAC yetki kontrolü, PID & bağımlılık kontrolü
├── config.py               # Tema renkleri, dosya imzaları (FILE_SIGNATURES) ve sabitler
├── ntfs.py                 # NTFS MFT tablosu okuyucu ve silinmiş dosya meta verisi ayıklayıcı
├── carver.py               # Sektör tabanlı Raw File Carver, thread worker döngüleri, imza eşleştirme
├── app_settings.json       # Uygulama ayarları (seçili kategoriler, tarama kuyruğu)
├── kurtarilan_dosyalar/    # Varsayılan dışa aktarım (recovery) klasörü
├── yedekler/               # Tarama seansları ve otomatik durum yedekleri (.json ve .txt raporlar)
└── ui/                     # Tkinter Arayüz Modülleri (Mixin Yapısı)
    ├── __init__.py         # RecoveryApp sınıfı dışa aktarımı
    ├── app.py              # Ana Tkinter uygulama sınıfı, mesaj kuyruğu (check_queue) ve yaşam döngüsü
    ├── drives.py           # Fiziksel sürücüleri (PhysicalDrive) PowerShell & raw read ile tespit etme
    ├── scan.py             # Gösterge tablosu tarama mantığı, seans kaydı ve blok haritası
    ├── preview.py          # Görsel (Pillow), video (OpenCV/MoviePy) ve ses önizleme modülü
    ├── export.py           # Bulunan dosyaları diske yazma ve ZIP ayıklama iş parçacıkları
    ├── tree.py             # Dosya Treeview (klasör ağacı) render etme, sıralama ve arama
    ├── gallery.py          # Bağımsız klasör galeri modu ve medya önizleme kartları
    └── layout.py           # GUI düzeni, sidebar, dashboard kartları ve stil tanımları
```

---

## 🚨 2. Kritik Buglar ve Çalışmama Riskleri

### 🔴 2.1 Hardcoded "Seagate" Disk Markası Kısıtlaması (Kritik İşlevsellik Engeli)
* **Konum:** [`ui/scan.py:L93`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ui/scan.py#L93) ve [`ui/gallery.py:L388`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ui/gallery.py#L388)
* **Açıklama:** Tarama başlatılacağı zaman `if "seagate" not in selected_disp.lower():` şeklinde sert bir denetim yapılmıştır.
* **Risk:** Kullanıcının diski **Samsung, Western Digital (WD), SanDisk, Kingston, Crucial, NVMe SSD, Sanal Disk veya USB Bellek** ise tarama **"Kritik Hata: Uyumsuz Sürücü!"** uyarısı vererek engellenmektedir. Uygulama Seagate dışındaki tüm disklerde kullanılamaz durumdadır.
* **Çözüm:** Bu kontrol tamamen kaldırılmalı veya isteğe bağlı bir uyarı/log mesajına dönüştürülmelidir.

---

### 🔴 2.2 UAC (Yönetici Yetkisi) İptali ve PID Yarış Durumu (Race Condition)
* **Konum:** [`main.py:L30-90`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/main.py#L30-L90)
* **Açıklama:**
  1. `main.py` çalışırken önce `enforce_single_instance()` çağrılarak `app.pid` dosyasına yetkisiz sürecin (non-admin PID) numarası yazılır.
  2. Ardından `run_as_admin()` çağrılır. Eğer kullanıcı admin değilse `ShellExecuteW` ile yönetici yetkisinde yeni bir süreç başlatılır ve `sys.exit(0)` denir.
  3. Yönetici yetkisinde açılan yeni süreç tekrar `enforce_single_instance()` çalıştırdığında `app.pid` içindeki eski (kapanmakta olan) PID'yi bulur ve `taskkill /F /PID {old_pid}` çalıştırmaya çalışır.
  4. Ayrıca kullanıcı UAC evet/hayır penceresinde **"Hayır" (İptal)** derse, `ctypes.windll.shell32.ShellExecuteW` Python istisnası fırlatmaz, hata kodu döner. Kod buna bakmadan `sys.exit(0)` çağırdığı için uygulama hiçbir hata mesajı vermeden **sessizce kapanır**.
* **Çözüm:** `run_as_admin()` denetimi `enforce_single_instance()` öncesinde yapılmalı; `ShellExecuteW` dönüş değeri kontrol edilerek UAC reddedildiğinde kullanıcıya bildirim gösterilmelidir.

---

### 🔴 2.3 NTFS MFT Silinmiş Dosya Meta Verisi Çakışması (`deleted_files` Overwrite Bug)
* **Konum:** [`ntfs.py:L252`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ntfs.py#L252)
* **Açıklama:** `deleted_files[f_info["offset"]] = { ... }` satırında sözlük (dict) anahtarı olarak doğrudan dosyanın başlangıç bayt offset'i (`offset`) kullanılmaktadır.
* **Risk:** Birden fazla silinmiş dosya henüz sektöre yazılmamışsa, resident veriyse veya offset'i `0` (ya da aynı cluster) ise, sözlükteki önceki silinmiş dosya bilgisi **üzerine yazılır (overwrite)**. Bu durum silinmiş dosyaların isim ve klasör yollarının kaybolmasına neden olur.
* **Çözüm:** Anahtar olarak `(offset, MFT_record_num)` ikilisi kullanılmalı veya liste yapısına geçilmelidir.

---

### 🔴 2.4 MFT Kayıt Numarası (Record Number) Offset Bağımlılığı
* **Konum:** [`ntfs.py:L210`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ntfs.py#L210)
* **Açıklama:** `record_num = int.from_bytes(record[44:48], "little")` satırı MFT başlığının 44. baytındaki MFT kayıt numarasını okur.
* **Risk:** Eski NTFS sürümlerinde veya bazı biçimlendirilmiş MFT kayıtlarında bu offset `0` durabilir. Bu durumda tüm klasörler `all_records[0]` üzerine yazılır ve silinmiş dosyaların Orijinal Klasör Yolu (`custom_path`) tamamen bozulur.
* **Çözüm:** `record[44:48]` sıfır geldiğinde taranan kayıt indeksinden (`records_read - 1`) kayıt numarası türetilmelidir.

---

### 🔴 2.5 Non-Resident $DATA Seyrek (Sparse) Cluster Offset Hatası
* **Konum:** [`ntfs.py:L203-204`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ntfs.py#L203-L204)
* **Açıklama:** `if data_runs: file_start_byte = partition_base_offset + (data_runs[0][0] * cluster_size)`
* **Risk:** `data_runs[0][0]` değeri `0` ise (sparse cluster / boş alan), `file_start_byte` doğrudan `partition_base_offset` (bölümün 0. sektörü) olarak hesaplanır. Carver bu offset'te yanlış meta veri eşleştirmesi yapabilir.
* **Çözüm:** `data_runs[0][0] > 0` şartı eklenmelidir.

---

### 🔴 2.6 Windows `PhysicalDrive` Aygıtlarında `f.seek(0, 2)` Başarısızlığı
* **Konum:** [`ui/drives.py:L56`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ui/drives.py#L56)
* **Açıklama:** PowerShell başarısız olduğunda fallback olarak `open(rf"\\.\PhysicalDrive{i}", "rb")` açılıp `f.seek(0, 2)` ile dosya sonuna gidilerek disk boyutu hesaplanmaya çalışılmaktadır.
* **Risk:** Windows işletim sisteminde ham fiziksel disk nesnelerinde (`PhysicalDrive`) standart C/Python `f.seek(0, 2)` çağrısı `OSError: [Errno 22] Invalid argument` fırlatır veya `0` döner.
* **Çözüm:** Disk boyutu tespiti için `ctypes` ile Win32 `DeviceIoControl` (`IOCTL_DISK_GET_DRIVE_GEOMETRY_EX`) kullanılmalı veya PowerShell `Get-Disk` sonucuna güvenilmelidir.

---

### 🔴 2.7 Arka Plan İş Parçacığında Doğrudan UI Nesnesi Değiştirme (Thread Safety)
* **Konum:** [`ui/drives.py:L9-11 ve L34-43`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ui/drives.py#L9-L43)
* **Açıklama:** `_async_load_drives()` fonksiyonu bir `threading.Thread` içinde çalışırken main thread'e ait `self.drives_map`, `self.drives_sizes_map` ve `self.drives_details_map` sözlüklerini doğrudan günellemektedir.
* **Risk:** Arayüz thread'i disk seçimi yaparken bu sözlükleri okursa Tkinter çökebilir veya yarış durumu (Race Condition) yaşanabilir.
* **Çözüm:** Sözlük güncellemeleri de `self.msg_queue` üzerinden ana thread'e iletilmelidir.

---

## ⚡ 3. Performans, Bellek (RAM) ve Arayüz Darboğazları

### 🟡 3.1 Cihaz Okuma Kilit Çakışması (`disk_lock` Contention)
* **Konum:** [`carver.py:L30-78`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/carver.py#L30-L78) ve [`ui/app.py:L75`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ui/app.py#L75)
* **Açıklama:** Paralel taramada (örneğin 16 worker thread seçildiğinde) tüm worker thread'ler aynı `disk_lock` kilidini beklemektedir.
* **Etki:** Çoklu iş parçacığı seçilse dahi tüm disk okumaları serileşmekte (single-thread IO hızı), beklenen performans artışı sağlanamamaktadır.
* **Çözüm:** Her worker thread'in kendi disk dosya tutamacını (handle) bağımsız açması sağlandığı için, okuma esnasındaki genel kilit dar tutulmalı veya devredışı bırakılmalıdır.

---

### 🟡 3.2 Tkinter Treeview Büyük Veri Seti Kilitlenmeleri (UI Lag)
* **Konum:** [`ui/tree.py:L176-195`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/ui/tree.py#L176-L195)
* **Açıklama:** `update_file_listbox_view` fonksiyonunda 50.000+ dosya bulunduğunda `self.after(5, ...)` ile 100'erli gruplar halinde binlerce özyinelemeli callback oluşturulmaktadır.
* **Etki:** Tkinter event döngüsü tıkanmakta, arayüz donmakta veya yanıt vermiyor durumuna düşmektedir.
* **Çözüm:** Ağaçta yalnızca görünür bölge veya klasör bazlı tembel yükleme (lazy loading / pagination) uygulanmalıdır.

---

### 🟡 3.3 MP4 ve ZIP Boyut Tespiti Sabit Fallback Riskleri
* **Konum:** [`carver.py:L225`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/carver.py#L225) (`return max(total_size, 15 * 1024 * 1024)`) ve [`carver.py:L265`](file:///c:/Users/User/Desktop/Disk%20Kurtarma/carver.py#L265) (`return 1024 * 1024`)
* **Açıklama:** MP4 kutusu (box) okuma veya ZIP EOCD imza taraması başarısız olduğunda MP4 için sabit 15 MB, ZIP için 1 MB varsayılan boyut dönülmektedir.
* **Etki:** 15 MB'tan büyük bir MP4 videosu veya 1 MB'tan büyük bir ZIP arşivi kurtarılırken dosya yarım kesilmekte ve bozulmaktadır.
* **Çözüm:** Sabit varsayılan boyut vermek yerine, bir sonraki imza offset'ine kadar tarama yapma veya sektörel sınır belirleme mekanizması eklenmelidir.

---

## 🛠️ 4. Mimari ve Kod Kalitesi Geliştirme Önerileri

### 💡 4.1 Monolitik Mixin Yapısından Modüler Yapıya Geçiş
* **Mevcut Durum:** `RecoveryApp` sınıfı 8 farklı Mixin (`DrivesMixin`, `ScanMixin`, `PreviewMixin`, `ExportMixin`, `TreeMixin`, `LayoutMixin`, `GalleryMixin`, `tk.Tk`) sınıfından türetilmiştir. Tüm durum değişkenleri `self` üzerinde toplandığı için isim çakışmaları (ör. `start_btn` vs `gallery_start_btn`) ve sıkı bağımlılık (tight coupling) oluşmuştur.
* **Öneri:** İş mantığı (Business Logic / Carver Core) ile Sunum Katmanı (UI Widgets) birbirinden kesin hatlarla ayrılmalı (MVC veya Event-Driven Controller mimarisi).

---

### 💡 4.2 Kod Tekrarlarının (Code Duplication) Temizlenmesi
* **Mevcut Durum:** `ui/scan.py` ile `ui/gallery.py` dosyalarında tarama başlatma, duraklatma, devam ettirme ve seans kaydetme kodları neredeyse %90 oranında birebir kopyalanmıştır (`start_recovery` vs `start_gallery_recovery`).
* **Öneri:** Ortak tarama denetimci mantığı tek bir `ScanController` sınıfında toplanmalı, hem Dashboard hem Galeri görünümü bu kontrolcüye bağlanmalıdır (DRY Prensibi).

---

### 💡 4.3 Bağımlılık Yönetiminin Standartlaştırılması
* **Mevcut Durum:** `main.py` içinde `pip install Pillow` ve `pip install moviepy` komutları çalışma anında `subprocess` ile çalıştırılmaktadır.
* **Öneri:** Proje kök dizinine standart `requirements.txt` eklenmeli, paket paketleme (PyInstaller .exe hale getirme) durumlarında çalışma zamanı pip yüklemelerinin hata vermesi engellenmelidir.

---

## 📋 5. Önceliklendirilmiş Eylem Planı (Roadmap)

| Öncelik | Modül / Dosya | Yapılacak İşlem | Hedef |
| :--- | :--- | :--- | :--- |
| 🔥 **P0 (Acil)** | `ui/scan.py` & `ui/gallery.py` | `"seagate"` harf duyarlı marka engelinin kaldırılması | Tüm disklerde çalışabilmesini sağlamak |
| 🔥 **P0 (Acil)** | `main.py` | UAC kontrolü ile PID dosya yazım sırasının düzeltilmesi | Başlatmada sessiz kapanma ve yarış durumunu çözmek |
| 🔴 **P1 (Yüksek)**| `ntfs.py` | `deleted_files` offset anahtar çakışması ve MFT index fallback düzeltmesi | Silinmiş dosya isimlerinin kaybolmasını önlemek |
| 🔴 **P1 (Yüksek)**| `ui/drives.py` | Background thread direct UI dict mutasyonlarının queue'ya alınması | Thread-safety ihlallerini ve UI çökmelerini önlemek |
| 🟡 **P2 (Orta)**  | `carver.py` | MP4/ZIP dinamik boyut tespiti ve kilit optimizasyonu | Büyük dosya verimliliğini artırmak |
| 🔵 **P3 (Düşük)** | `ui/` Mimari | `scan.py` ve `gallery.py` ortak tarama kodlarının birleştirilmesi | Kod kalitesi ve sürdürülebilirlik |

---

> ℹ️ *Bu rapor, projenin mevcut durumu incelenerek otomatik analiz araçları ve antitez incelemeleri ile hazırlanmıştır.*
