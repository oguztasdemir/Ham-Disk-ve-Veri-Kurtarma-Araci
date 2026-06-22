# 🛠️ Disk Drill - Professional Data Recovery & File Carver

Disk Drill, Windows sistemleri için geliştirilmiş, ham sektör düzeyinde (Raw Sector-level) çalışan, çoklu iş parçacığı (Multi-threading) destekli ve yüksek performanslı bir veri kurtarma ve dosya oymacılığı (File Carving) yazılımıdır. 

Hızlı biçimlendirilmiş (Quick Formatted) veya dosya yapısı bozulmuş diskler üzerinde ham disk okuması yaparak dosya imzalarından (Magic Bytes/Header-Footer) dosyaları tespit eder ve bilgisayara indirmeden önce görsel olarak klasörlemenize olanak tanır.

---

## ✨ Öne Çıkan Özellikler

### 1. 🚀 Donanım Limitinde Tarama Hızı (Concurrent Multi-threading)
- Her tarama motoru (Worker Thread) disk üzerinde kendine özel, ön-belleğe alınmamış (unbuffered/direct I/O) okuma kolları açar.
- Global disk kilidi (`disk_lock`) yerine **iş parçacığına özel kilitler (worker_lock)** kullanılarak eşzamanlı veri seek/read işlemleri tamamen bağımsız hale getirilmiştir. Bu sayede 1.8 TB ve üzeri diskler donanımın maksimum okuma hızında taranır.

### 2. 📊 Görsel Disk Durum Haritası (Visual Disk Map)
- Arama yapılan diski 100 bloğa bölen, defragmenter tarzı interaktif bir durum haritası sunar:
  - 🔵 **Mavi (Taranmadı)**: Henüz taranmamış ham sektörler.
  - 🟠 **Turuncu (Taranıyor)**: O anda taranmakta olan anlık okuma başlığı.
  - 🟢 **Yeşil (Tarandı)**: Başarıyla taranmış ve analiz edilmiş disk bölgeleri.
- Oturum kaydetme (`scan_state.json`) özelliği sayesinde tarama yarıda kesilip tekrar açıldığında haritadaki yeşil bölgeler korunur.

### 3. 📁 Sanal Klasörleme ve Çoklu Seçim (Virtual Folder & Multi-Select)
- Bulunan dosyaları bilgisayara **kurtarmadan önce** sanal klasörlere ve alt klasörlere (Örn: `Resimler/Tatil`) dağıtabilirsiniz.
- `Shift + Sol Tık` (aralıklı toplu seçim) ve `Ctrl + Sol Tık` (tekil çoklu seçim) ile dosyaları seçerek **"Seçilenleri Klasöre Taşı"** diyebilir ve hiyerarşik yapınızı oluşturabilirsiniz. 
- Dışa aktarım yaparken program bu sanal klasör yapısına sadık kalarak dosyaları fiziksel olarak yazar.

### 4. 🔍 Anlık Arama ve Gelişmiş Sıralama
- Binlerce dosya arasından hızlıca filtreleme yapabilmeniz için anlık tepki veren **"🔍 Ara"** çubuğu.
- Dosya adına göre doğal sıralama (Natural Sorting: `kurtarilan_10.jpg` dosyasını `kurtarilan_2.jpg`'den sonra sıralar), boyut ve disk ofsetine göre sıralama.

### 5. 🏥 S.M.A.R.T Sağlık ve Disk Teşhisi
- Arayüzden bir disk seçtiğiniz anda, Windows API'leri ve PowerShell WMI katmanı üzerinden diskin:
  - Model Adı
  - SMART Sağlık Durumu (Sağlıklı / Kritik / Uyarı)
  - Bölümleme Tablosu Stili (GPT / MBR)
  - Gerçek Kapasite değerleri anlık olarak sorgulanır ve gösterge panelinde listelenir.

### 6. 🛠️ Otomatik Dosya Onarımı (Auto-Repair & Stream Extractor)
- **JPEG/JPG**: Sektör hizalaması nedeniyle oluşan null padding'ler temizlenir, eksik footer (`FFD9`) imzası otomatik tamamlanarak resimlerin bozulması önlenir.
- **MP4**: `moov` kutusu eksik olduğu için oynatılamayan videolarda, ham video kareleri (Annex B byte stream) ayıklanarak oynatılabilir `.h264` akışına dönüştürülür.

### 7. 🔌 Tak-Çalıştır ve Sıfır Kurulum (Zero-Config Portability)
- Program açılırken `Pillow` kütüphanesinin yüklü olup olmadığını otomatik olarak kontrol eder. Kütüphane eksik ise arka planda otomatik olarak `pip` ile kurarak programın hatasız açılmasını sağlar.

---

## 🛠️ Kurulum ve Çalıştırma

### Gereksinimler
- Windows 10 / 11
- Python 3.8 veya daha yeni bir sürüm

### Çalıştırma
Uygulama fiziksel disklerin (Raw Sector) ham verilerini okuduğu için **Yönetici Yetkileri (Administrator)** ile çalıştırılmalıdır. `main.py` bunu otomatik olarak algılayıp onay ister.

Projeyi indirin ve konsola şu komutu yazın:

```bash
python main.py
```

---

## 📂 Proje Yapısı

```text
Disk Kurtarma/
│
├── main.py                # Uygulama Giriş Noktası (Yönetici yetkisi & Bağımlılık kontrolü)
├── carver.py              # File Carving imza eşleştirme, dosya okuma ve kurtarma motoru
├── ntfs.py                # Silinmiş NTFS MFT kayıtlarını oyan ve isim eşleyen alt yapı
├── config.py              # Desteklenen dosya kategorileri, magic byte imzaları ve renk şemaları
│
└── ui/                    # Arayüz Bileşenleri (Mixin Yapısı)
    ├── __init__.py        
    ├── app.py             # Ana uygulama döngüsü ve mesaj kuyruğu yönetimi
    ├── layout.py          # Modern tasarım yerleşimi ve SMART bilgi kartı
    ├── tree.py            # Recursive sanal klasör yönetimi ve çoklu seçim fonksiyonları
    ├── scan.py            # Tarama başlatma, duraklatma ve durum kaydetme/yükleme
    ├── drives.py          # Fiziksel diskleri ve SMART sağlık verilerini getiren modül
    ├── preview.py         # Resim ve metin tabanlı önizleme modülü
    └── export.py          # Dosyaları fiziksel disk üzerine yazan ve onaran modül
```

