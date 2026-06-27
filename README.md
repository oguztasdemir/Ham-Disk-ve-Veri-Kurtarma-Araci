# 🛠️ NovaRecovery - Professional Data Recovery & File Carver

NovaRecovery, Windows işletim sistemleri için geliştirilmiş, ham sektör düzeyinde (Raw Sector-level) çalışan, çoklu iş parçacığı (Multi-threading) destekli, yüksek performanslı ve modern bir veri kurtarma ve dosya oymacılığı (File Carving) yazılımıdır. 

Hızlı biçimlendirilmiş (Quick Formatted), dosya yapısı bozulmuş (RAW) veya silinmiş veriler barındıran diskler üzerinde doğrudan sektör okuması yaparak dosya imzalarından (Magic Bytes/Header-Footer) dosyaları kurtarır. Bulunan dosyaları bilgisayara kaydetmeden önce görsel olarak önizlemenize, klasörlemenize ve otomatik olarak hedef diske yedeklemenize olanak tanır.

---

## ✨ Öne Çıkan Yetenekler

### 1. 🚀 Donanım Limitinde Tarama Hızı (Concurrent Multi-threading)
- Her tarama motoru (Worker Thread) disk üzerinde kendine özel, ön-belleğe alınmamış (unbuffered/direct I/O) okuma kolları açar.
- Global disk kilidi yerine **iş parçacığına özel kilitler (worker_lock)** kullanılarak eşzamanlı veri seek/read işlemleri tamamen bağımsız hale getirilmiştir. Bu sayede diskler donanımın maksimum okuma hızında taranır.

### 2. 📊 Görsel Disk Durum Haritası (Visual Disk Map) & Blok Manuel Müdahale
- Arama yapılan diski 100 bloğa bölen, defragmenter tarzı interaktif bir durum haritası sunar:
  - 🔵 **Mavi (Taranmadı)**: Henüz taranmamış ham sektörler.
  - 🟠 **Turuncu (Taranıyor)**: O anda taranmakta olan anlık okuma başlığı.
  - 🟢 **Yeşil (Tarandı)**: Başarıyla taranmış ve analiz edilmiş disk bölgeleri.
- **Hassas Konum Rezervasyonu**: Tarama duraklatılıp veya durdurulup tekrar başlatıldığında ya da blok seçimi değiştirildiğinde, taranmış alanlar akıllıca atlanır. Kısmen taranmış segmentler (örneğin %30 taranmış) **tam olarak kaldıkları byte/sektör ofsetinden** itibaren taramaya devam eder.
- **Blok Sıfırlama ve Fulleme (Sıfırla / Fulle)**: Disk haritası detay penceresinde seçili blokların tarama ilerlemeleri anlık olarak sıfırlanabilir veya dolu (%100 taranmış) olarak işaretlenebilir. Sistem bu manuel müdahalelere göre dinamik olarak ilerler.

### 3. 🔍 Gelişmiş Önizleme ve Bütünlük Doğrulaması (Preview & Integrity Verification)
- **Sıkı Doğrulama ve Filtreleme**: Bozuk, eksik veya rastgele imza eşleşmelerini önlemek adına bulunan resimler (JPEG, PNG vb.) ve videolar (MP4) arka planda Pillow ve OpenCV yardımıyla tamamen doğrulanır. Doğrulamayı geçemeyen (önizlenemeyen) dosyalar **sonuç listesine eklenmez**, elenerek "İstem Dışı Öğe" olarak sayılır.
- **Hasarlı Resim Kurtarma (Truncated Image Support)**: Pillow'un `LOAD_TRUNCATED_IMAGES` modu entegre edilmiştir. Hafif hasarlı, kesintiye uğramış veya yarım kalmış resimler çöpe atılmak yerine kurtarabildiği kadarıyla çözümlenip önizlenebilir ve geri kazanılabilir hale getirilir.
- **Ayarlar Sekmesi**: Önizleme doğrulama seviyesini ve minimum dosya boyutu gibi parametreleri özelleştirebilirsiniz.

### 4. 📺 YouTube Tarzı Video Oynatıcı & Gelişmiş Önizleme
- Bir video dosyası seçildiği anda arka planda ilk karesi çözümlenerek **görsel (thumbnail)** olarak ekrana basılır ve video süresi gösterilir.
- Video ekranının ortasına YouTube tarzı büyük bir oynatma (`▶`) butonu yerleştirilmiştir. Videoya veya oynatma butonuna tıklandığında oynatma başlar/durur (orta buton oynatılırken gizlenir).
- `pygame.mixer` ses motoru, Python 3.13 uyumlu ve statik uyarı vermeyecek şekilde optimize edilmiştir.

### 5. 📁 Sanal Klasörleme, Proximity (Yakınlık) Yolu & Çoklu Seçim
- **NTFS MFT Yakınlık Algoritması**: Silinmiş NTFS kayıtları (MFT tablosu) ile ham imza taramasından elde edilen ofsetleri eşleştirmek için **256 KB Proximity** ve dosya uzantı filtresi entegre edilmiştir. Bu sayede dosyaların orijinal adları, değiştirilme tarihleri ve orijinal klasör yolları (örneğin `ben-good`) çok yüksek başarı oranıyla geri kazanılır ve ağaç yapısı otomatik kurulur.
- Bulunan dosyaları bilgisayara **kurtarmadan önce** sanal klasörlere dağıtabilir, `Shift / Ctrl + Sol Tık` ile çoklu seçim yaparak klasör hiyerarşisi oluşturabilirsiniz.

### 6. 💾 Gerçek Zamanlı Otomatik Dışa Aktarma & İptal Desteği
- **30 Saniyede Bir Eşzamanlı Yedekleme**: Tarama devam ederken bulunan tüm yeni ve sağlam dosyalar, oturum yedeğiyle birlikte **30 saniyede bir** doğrudan hedef diske aktarılır.
- Dosyalar diske çıkartılırken `klasor1`, `klasor2` gibi karmaşık isimler yerine arayüzdeki hiyerarşinin birebir aynısıyla (Örn: `/Resim/jpg/file/` veya `/ben-good/`) düzenli bir şekilde fiziksel klasörlere yazılarak kaydedilir.
- Dışa aktarma öncesi hedef disk alan sorgulaması yapılır ve uzun süren işlemlerde arayüz kilitlenmeden güvenli "İptal Et" desteği sağlanır.

### 7. 🔍 Anlık Arama, Mükerrer Eşleşme Önleme ve SMART Teşhisi
- **Mükerrer Dosya Filtresi (Duplicate Skipping)**: Tarama sırasında daha önce bulunmuş (aynı başlangıç ofsetine sahip) mükerrer dosyalar pas geçilir ve ilgili bloğun **Kopya** sayacı artırılarak detay listesinde gösterilir.
- Anlık filtreleme sunan **"Ara"** çubuğu ve dosya adına göre doğal sıralama (Natural Sorting).
- Disk seçildiği anda Windows API'leri üzerinden SMART Sağlık Durumu (Sağlıklı / Kritik), Bölümleme Tablosu Stili (GPT/MBR) ve gerçek kapasite analizi.

### 8. 🛠️ Gelişmiş Otomatik Dosya Onarımı (Auto-Repair & Stream Extractor)
- **JPEG/JPG**: Hizalamadan kaynaklı null padding'ler temizlenir, eksik footer (`FFD9`) imzası otomatik tamamlanır.
- **MP4**: `moov` kutusu eksik olan videolarda, ham video kareleri (Annex B byte stream) ayıklanarak oynatılabilir `.h264` akışına dönüştürülür.
- **Office Belgeleri (.docx, .xlsx, .pptx)**: ZIP arşivleri analiz edilir; içeriklerinde MS Office imzaları (`word/`, `xl/`, `ppt/`) saptanırsa otomatik olarak ilgili formatta `Belge` kategorisine atanır.

---

## 🚀 Projeyi Kurma ve Başlatma (Adım Adım)

Uygulamanın çalışması için bilgisayarınızda Python kurulu olmalı ve işletim sisteminde disklerin ham sektörlerine doğrudan erişim sağlayabilmek için yönetici (Administrator) yetkisiyle çalıştırılması gerekmektedir.

### Adım 1: Python Kurulumu
1. Bilgisayarınızda Python yüklü değilse, [python.org](https://www.python.org/) adresinden **Python 3.10 veya daha yeni** sürümünü indirin.
2. Kurulum ekranında **"Add Python to PATH"** seçeneğini mutlaka işaretleyin.

### Adım 2: Terminali (Komut Satırını) Yönetici Olarak Açma
Fiziksel disk sürücülerine (örneğin `\\.\PhysicalDrive1`) doğrudan okuma talebi göndermek Windows güvenlik politikaları nedeniyle kısıtlanmıştır. Bu nedenle:
1. Windows arama çubuğuna `cmd` veya `PowerShell` yazın.
2. Çıkan sonuca sağ tıklayıp **"Yönetici Olarak Çalıştır"** (Run as Administrator) seçeneğine tıklayın.

### Adım 3: Proje Dizinine Geçiş
Yönetici olarak açılan komut satırında proje dosyalarının bulunduğu klasöre `cd` komutu ile geçiş yapın:
```cmd
cd "C:\Users\User\Desktop\Disk Kurtarma"
```

### Adım 4: Uygulamayı Başlatma
Projede gerekli olan kütüphaneler (`Pillow`, `pygame`, `moviepy`, `opencv-python`) **ilk açılışta program tarafından otomatik olarak denetlenir ve eksikse kurulur.** Sizin manuel olarak `pip` komutu çalıştırmanıza gerek yoktur.

Uygulamayı başlatmak için terminale şu komutu yazın:
```cmd
python main.py
```
*Not: Eğer yönetici olarak çalıştırmayı unuttuysanız, `main.py` bunu algılayıp sizden otomatik olarak yönetici izni (UAC) talep edecektir.*

---

## 📂 Proje Modülleri ve Dosya Yapısı

```text
Disk Kurtarma/
│
├── main.py                # Uygulama Giriş Noktası (Yönetici yetkisi, tekil oturum ve bağımlılık kontrolü)
├── carver.py              # File Carving imza eşleştirme, dosya okuma ve bütünlük doğrulama motoru
├── ntfs.py                # Silinmiş NTFS MFT kayıtlarını okuyan ve 256KB yakınlık bazlı eşleme yapan altyapı
├── config.py              # Desteklenen dosya kategorileri, magic byte imzaları ve renk şemaları
│
└── ui/                    # Arayüz Bileşenleri (Mixin Yapısı)
    ├── __init__.py        
    ├── app.py             # Ana uygulama döngüsü, mesaj kuyruğu yönetimi ve 30sn auto-export tetikleyicisi
    ├── layout.py          # Modern tasarım yerleşimi, SMART bilgi kartı ve Önizleme Kontrol Paneli
    ├── tree.py            # Sanal klasör yönetimi, sürükle-bırak ve Shift/Ctrl çoklu seçim fonksiyonları
    ├── scan.py            # Tarama durum kontrolü, oturum kaydetme/yükleme ve yedek alma entegrasyonu
    ├── drives.py          # Fiziksel diskleri ve SMART sağlık verilerini getiren modül
    ├── preview.py         # Resim, video (YouTube tarzı oynatıcı) ve metin önizleme modülü
    └── export.py          # Dosyaları disk alanını kontrol ederek kurtaran, onaran ve güvenle yazan modül
```

---

## 📝 Kullanım İpuçları

1. **Önce Kurtarma Konumu Seçin:** Taramayı başlatmadan önce sağ taraftaki **"Taşınacak Yeri Seçin"** butonu ile kurtarılan dosyaların yedekleneceği hedef dizini belirleyin. (Hedef dizin kesinlikle taranan diskin kendisi olmamalıdır!).
2. **Kaldığı Yerden Devam Etme:** Tarama herhangi bir aşamada durdurulduğunda, **"Yedek Al"** diyerek oturumunuzu kaydedebilir, daha sonra programı yeniden açtığınızda **"Oturumu Değiştir"** seçeneğiyle yedeği yükleyip tam kaldığı sektörden devam ettirebilirsiniz.
3. **Detaylı Harita Analizi:** Disk Map üzerindeki herhangi bir bloğa çift tıklayarak o bölgenin detaylı durumunu, o blokta kaç adet kopya (tekrarlanan veri) veya kaç adet istem dışı (bozuk/kriter dışı) veri çıktığını görebilir, dilerseniz seçtiğiniz bloğun ilerlemesini sıfırlayabilirsiniz.
4. **Sanal Klasörleme:** Tarama sırasında bulunan görselleri arayüzdeki listeden `Ctrl + Sol Tık` veya `Shift + Sol Tık` ile toplu seçip **"Seçilenleri Klasöre Taşı"** butonuyla istediğiniz kategorilere taşıyarak diske çıkmadan önce hiyerarşinizi düzenleyebilirsiniz.

## 📝 Lisans

Bu proje **MIT Lisansı** altında lisanslanmıştır. Eğitim ve veri kurtarma araştırmaları amacıyla geliştirilmiştir. Ticari kullanımlarda disk üzerindeki ham veri yapılarına doğrudan erişim sağlandığından dikkatli olunması önerilir.
