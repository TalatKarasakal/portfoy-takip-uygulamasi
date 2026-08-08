# 📌 Portföy Takip ve Analiz Uygulaması — Proje Takip ve Sorun Yönetim Belgesi

Bu belge; uygulamadaki yapılacak işleri, tespit edilen sorunları, önerilen/uygulanan çözümleri, geliştirici onayına sunulan maddeleri ve geliştirme fikirlerini takip etmek için kullanılır.

---

## 📋 1. Yapılacaklar (To-Do & Not Defteri)
> Gelecekte yapılmak üzere kaydedilen fikirler, küçük notlar ve zamanı geldiğinde ele alınacak işler.

- [ ] **[Öncelik: Orta]** Piyasa saatlerinde otomatik fiyat güncelleyen arka plan zamanlayıcısının (`QTimer`) aktif edilmesi.
- [ ] **[Öncelik: Düşük]** TEFAS fonları ve küsüratlı lotlar için ondalık basamak hassasiyetinin (4-6 hane) ayarlanması.
- [ ] **[Öncelik: Düşük]** Veritabanı sorgu performansını artırmak için `transactions` ve `price_history` tablolarına composite indeksler eklenmesi.

---

## ⚠️ 2. Tespit Edilen Sorunlar ve Çözüm Önerileri
> Uygulamada karşılaşılan teknik ve fonksiyonel sorunlar ile önerilen çözümler.
> *Not: Öneriyi sunan model adı belirtilir ki diğer geliştiriciler ve agent'lar kendi süzgeçlerinden geçirebilsin.*

### 🟢 Sorun #1: `datetime.utcnow()` Amortisman (Deprecation) Uyarısı
- **Durum:** Açık
- **Açıklama:** Python 3.12+ ile `datetime.utcnow()` kullanımı amortismana uğramıştır. Testlerde ve loglarda 10 adede yakın `DeprecationWarning` üretmektedir.
- **Önerilen Çözüm [Gemini 3.6 Flash]:** `app/models/asset.py`, `transaction.py` ve `alert.py` modellerindeki `default=datetime.utcnow` tanımları `lambda: datetime.now(timezone.utc)` veya SQLAlchemy `func.now()` ile değiştirilmelidir.

### 🟢 Sorun #2: Loader Thread İçinde ORM Nesnelerinin Eşzamanlı Paylaşımı
- **Durum:** Açık
- **Açıklama:** `PortfolioLoaderThread` içerisinde `ThreadPoolExecutor` iş parçacıklarına doğrudan veritabanı oturumuna bağlı `Asset` ORM nesneleri aktarılmaktadır. Bu durum SQLAlchemy oturumunda yarış koşullarına (race condition) yol açabilir.
- **Önerilen Çözüm [Gemini 3.6 Flash]:** Worker fonksiyonuna ORM nesnesi yerine sadece ilkel veri tiplerini içeren tuple `(asset.id, asset.code, asset.asset_type)` iletilmelidir.

### 🟢 Sorun #3: Test Oturumlarında Kapanmayan SQLite Bağlantıları
- **Durum:** Açık
- **Açıklama:** `pytest` çalıştırıldığında `ResourceWarning: unclosed database` uyarıları alınmaktadır.
- **Önerilen Çözüm [Gemini 3.6 Flash]:** `conftest.py` içerisindeki SQLite veritabanı fixture'larına `yield` sonrası açık session ve engine kapatma adımları eklenmelidir.

### 🟢 Sorun #4: Benchmark Servisinde Çevrimdışı Durum Yönetimi
- **Durum:** Açık
- **Açıklama:** İnternet kesintisinde BIST 100 veya Altın kıyaslama verileri çekilemediğinde hata yakalanmalı ve kullanıcıya çevrimdışı uyarısı verilmelidir.
- **Önerilen Çözüm [Gemini 3.6 Flash]:** Network hatası durumunda boş liste dönülüp View tarafında "Veri Alınamadı" bildirimi gösterilmelidir.

### 🔴 Sorun #5: Excel Dışa Aktarımının Güvenli Biçimde Geri Alınamaması
- **Durum:** Açık
- **Öncelik:** Kritik
- **Açıklama:** Uygulamanın dışa aktardığı işlem sütunları (`Varlık Kodu`, `İşlem Türü`, `Ort. Maliyet`) ile içe aktarıcının beklediği sütunlar (`Kod`, `Tür`, `Ortalama Maliyet`) uyuşmamaktadır. Tarih alanları da Python `date` nesnesine dönüştürülmeden ORM'e gönderilmektedir. Yapılan yeniden üretimde dışa aktarılan 100,1 TL maliyetli pozisyon, içe aktarım sonrasında 0 TL maliyetli işlem olarak kaydedilmiş; tam işlem dosyası ise tarih tipi hatasıyla yüklenememiştir. Yardımcı metotların ayrı ayrı `commit()` çağırması dosyanın kısmen yüklenmesine de yol açabilir.
- **Önerilen Çözüm [GPT-5]:** Sütun adları tek bir kanonik şemada normalize edilmeli; tarih, sayı ve işlem türleri açıkça doğrulanmalı; dosyanın tamamı tek veritabanı transaction'ında işlenmeli ve hata halinde eksiksiz rollback yapılmalıdır. Uygulamanın kendi çıktısı için export → import round-trip testi eklenmelidir.

### 🔴 Sorun #6: Geçersiz ve Portföy Bakiyesini Aşan İşlemlerin Kaydedilebilmesi
- **Durum:** Açık
- **Öncelik:** Kritik
- **Açıklama:** Manuel giriş, Excel aktarımı ve asistan üzerinden eklenen işlemlerde ortak bir alan doğrulama katmanı yoktur. Negatif/sıfır değerler, gelecek tarihli işlemler ve eldeki adedi aşan satışlar veri katmanında engellenmemektedir. Yapılan yeniden üretimde 10 adet varlığa karşı 15 adet satış bakiyeyi `-5` bırakmış; WAC 300 TL, FIFO/LIFO ise 800 TL gerçekleşmiş kâr hesaplamıştır.
- **Önerilen Çözüm [GPT-5]:** Tüm giriş kanallarının kullandığı merkezi ve tip tanımlı bir `TransactionService` oluşturulmalıdır. Miktar, fiyat, komisyon, vergi, tarih, split oranı ve satılabilir bakiye burada doğrulanmalı; kısa pozisyon desteklenmiyorsa fazla satış kesin olarak reddedilmelidir.

### 🔴 Sorun #7: Yedek Başarısız Olsa Bile Tüm Verilerin Silinmesi
- **Durum:** Açık
- **Öncelik:** Kritik
- **Açıklama:** `SettingsViewModel.delete_all_data()` yedekleme sonucunu kontrol etmeden silme işlemine devam etmekte ve kullanıcıya yedek alındığını bildirmektedir. Ayrıca çalışan SQLite dosyası `shutil.copy2()` ile kopyalanmakta; geri yükleme öncesinde dosyanın SQLite bütünlüğü ve beklenen şemaya ait olup olmadığı doğrulanmamaktadır.
- **Önerilen Çözüm [GPT-5]:** Yedek alınamazsa silme işlemi durdurulmalıdır. Kopyalama için SQLite Backup API kullanılmalı; geri yükleme öncesinde `PRAGMA quick_check`, şema sürümü ve gerekli tablolar doğrulanmalı; dosya atomik olarak değiştirilmeden önce SQLAlchemy bağlantı havuzu kapatılmalıdır.

### 🔴 Sorun #8: Gemini API Anahtarının Loglara Sızabilmesi
- **Durum:** Açık
- **Öncelik:** Kritik
- **Açıklama:** Gemini anahtarı URL query parametresi olarak gönderilmektedir. `HTTPStatusError` metni URL'yi içerdiğinden hata logları API anahtarını açık biçimde kaydedebilir. Anahtar ayrıca SQLite `settings` tablosunda düz metin tutulmaktadır. Bulut sağlayıcısına hangi portföy bilgilerinin gönderildiğini açıklayan belirgin bir kullanıcı onayı da bulunmamaktadır.
- **Önerilen Çözüm [GPT-5]:** Anahtar desteklenen güvenli header üzerinden gönderilmeli, tüm log ve kullanıcı hata mesajlarında sırlar maskelenmeli ve işletim sistemi anahtar zincirinde saklanmalıdır. Bulut sağlayıcısı ilk kez etkinleştirilirken gönderilecek veri kapsamı açıklanıp açık onay alınmalıdır.

### 🟠 Sorun #9: Performans ve K/Z Yüzdelerinin Yanıltıcı Olabilmesi
- **Durum:** Açık
- **Öncelik:** Yüksek
- **Açıklama:** Snapshot değerindeki değişimler nakit giriş/çıkışlarından arındırılmadığı için yeni alımlar Sharpe, volatilite, maksimum düşüş ve aylık getiri hesaplarına yatırım performansı gibi yansımaktadır. Toplam K/Z yüzdesinde ise kapatılmış pozisyonların gerçekleşmiş kârı, yalnızca mevcut açık pozisyonların maliyetine bölünmektedir.
- **Önerilen Çözüm [GPT-5]:** Para yatırma/çekme akışları ayrı tutulmalı ve nakit akışından arındırılmış TWR hesaplanmalıdır. Gerçekleşmiş getiri, açık pozisyon getirisi ve toplam dönem getirisi ayrı metrikler olarak gösterilmeli; metriklerin tanımı arayüz araç ipuçlarında açıklanmalıdır.

### 🟠 Sorun #10: XIRR Hesabının Yakınsamayan Sonucu Geçerli Kabul Etmesi
- **Durum:** Açık
- **Öncelik:** Yüksek
- **Açıklama:** Newton-Raphson yöntemi yakınsamadığında fonksiyon son tahmini sonuç olarak döndürmektedir. Yalnızca pozitif veya yalnızca negatif nakit akışlarında yapılan yeniden üretimde yaklaşık `1.98e277` gibi anlamsız bir değer elde edilmiştir.
- **Önerilen Çözüm [GPT-5]:** Hesaplama öncesinde en az bir pozitif ve bir negatif nakit akışı şartı aranmalı; güvenli aralık kullanan kök bulma yöntemi tercih edilmeli; yakınsama sağlanamazsa sayısal değer yerine `hesaplanamadı` durumu döndürülmelidir.

### 🟠 Sorun #11: Aynı Günlü İşlemlerin Maliyet Hesabında Belirsiz Sıralanması
- **Durum:** Açık
- **Öncelik:** Yüksek
- **Açıklama:** Maliyet hesabı işlemleri yalnızca tarihe göre sıralamaktadır. Aynı gün gerçekleşen alım, satış, temettü veya split işlemlerinin sırası veritabanının dönüş sırasına bağlı kalabilir ve farklı maliyet/K/Z sonuçları oluşabilir.
- **Önerilen Çözüm [GPT-5]:** İşlemler en az `(date, id)` ile deterministik sıralanmalı; gün içi kesin sıranın önemli olduğu kullanım için ayrı bir `sequence` veya işlem zamanı alanı değerlendirilmelidir.

### 🟠 Sorun #12: Manuel Yenileme Butonunun Önbelleği Atlamaması
- **Durum:** Açık
- **Öncelik:** Orta
- **Açıklama:** `Şimdi Yenile` butonu `PortfolioViewModel.load_data()` metodunu varsayılan parametrelerle çağırmaktadır. Bu nedenle kullanıcı 15 dakikalık önbellek süresi içinde manuel yenileme yaptığında eski fiyatlar gösterilmeye devam edebilir.
- **Önerilen Çözüm [GPT-5]:** Manuel buton `load_data(force_refresh=True)` çağırmalı; yenileme sürerken gelen zorunlu yenileme isteğinin `force_refresh` bilgisi kuyrukta korunmalıdır.

### 🟠 Sorun #13: TEFAS İstek Sınırının Paralel Çağrılarda Uygulanmaması
- **Durum:** Açık
- **Öncelik:** Yüksek
- **Açıklama:** Portföy fiyatları `ThreadPoolExecutor(max_workers=10)` ile paralel alınmaktadır. Her TEFAS worker'ının ayrı ayrı 500 ms beklemesi, isteklerin aynı anda gönderilmesini engellemez. Paylaşılan `Crawler` nesnesinin eşzamanlı kullanımı da güvenilir değildir.
- **Önerilen Çözüm [GPT-5]:** TEFAS çağrıları için süreç genelinde monotonic zaman ve kilit kullanan merkezi rate limiter oluşturulmalı; crawler erişimi seri hale getirilmeli veya her worker için izole istemci kullanılmalıdır.

### 🟠 Sorun #14: Veritabanı Şema Geçişlerinin ve Foreign Key Kontrolünün Olmaması
- **Durum:** Açık
- **Öncelik:** Yüksek
- **Açıklama:** Uygulama açılışta yalnızca `Base.metadata.create_all()` çalıştırmaktadır; bu işlem mevcut tabloları yeni şemaya yükseltmez. Alembic bağımlılığı bulunmasına rağmen migration ortamı yoktur. SQLite bağlantılarında foreign key doğrulaması da açıkça etkinleştirilmemiştir.
- **Önerilen Çözüm [GPT-5]:** Alembic migration zinciri ve şema sürümü oluşturulmalı; açılışta gerekli migration'lar yedek alınarak uygulanmalı; her SQLite bağlantısında `PRAGMA foreign_keys=ON` ve uygun `busy_timeout` etkinleştirilmelidir.

### 🟠 Sorun #15: Dağıtım ve Paketleme Yapılandırmasının Temiz Klonda Çalışmaması
- **Durum:** Açık
- **Öncelik:** Yüksek
- **Açıklama:** `pyproject.toml` yalnızca `app` paketini ve `main` modülünü tanımlamakta; alt paketler, `mac_identity.py`, ikon, font ve QSS kaynakları kurulabilir pakete eksik girebilir. PyInstaller `.spec` dosyası `.gitignore` tarafından dışlandığından README'deki paketleme komutu temiz klonda çalışmayacaktır.
- **Önerilen Çözüm [GPT-5]:** Setuptools package discovery ve package-data yapılandırılmalı; giriş noktasının tüm modülleri pakete dahil edilmelidir. Tekrarlanabilir PyInstaller spec dosyası repoda izlenmeli ve CI içinde en az bir paket oluşturma smoke testi çalıştırılmalıdır.

### 🟡 Sorun #16: Bazı Ağ İşlemlerinin UI Thread'ini Dondurması ve Worker Kapanışlarının Eksikliği
- **Durum:** Açık
- **Öncelik:** Orta
- **Açıklama:** Sağlayıcı bağlantı testi ve yüzdelik Excel içe aktarımı ana UI thread'inde ağ çağrıları yapabilmektedir. Uygulama kapanırken çalışan portföy yükleme thread'i için de açık bir iptal/bekleme akışı bulunmamaktadır.
- **Önerilen Çözüm [GPT-5]:** Uzun süren tüm ağ ve dosya işlemleri ViewModel tarafından yönetilen worker'lara taşınmalı; ilerleme/iptal sinyalleri eklenmeli ve ana pencere kapanırken çalışan thread'ler kontrollü biçimde sonlandırılmalıdır.

### 🟡 Sorun #17: View Katmanındaki Doğrudan Servis Bağımlılıkları
- **Durum:** Açık
- **Öncelik:** Orta
- **Açıklama:** `analytics_view.py`, `settings_view.py` ve `ai_assistant_view.py` içerisinde servis modüllerine doğrudan erişimler bulunmaktadır. Hesaplama, benchmark yükleme ve sağlayıcı testi gibi akışlar View içinde yürütülerek MVVM sınırı zayıflatılmaktadır.
- **Önerilen Çözüm [GPT-5]:** View yalnızca kullanıcı etkileşimi ve render sorumluluğu taşımalı; servis çağrıları, hesaplama ve asenkron iş yönetimi ilgili ViewModel katmanına taşınmalıdır.

### 🟡 Sorun #18: Önbellek Sürelerinin Dokümantasyonla Uyuşmaması
- **Durum:** Açık
- **Öncelik:** Düşük
- **Açıklama:** Döviz kuru için 24 saat, benchmark için 6 saat ve fon adı için uzun süreli önbellek ifade edilmesine rağmen bütün anahtarlar ortak 15 dakikalık `PriceCache.DEFAULT_TTL` değerini kullanmaktadır.
- **Önerilen Çözüm [GPT-5]:** `PriceCache.set()` anahtar bazlı TTL kabul etmeli; fiyat, kur, benchmark ve fon adı için tanımlanan süreler teknik spesifikasyonla eşleştirilmelidir.

### 🟡 Sorun #19: Test ve CI Kapsamının Kritik Kullanıcı Akışlarını İçermemesi
- **Durum:** Açık
- **Öncelik:** Orta
- **Açıklama:** Mevcut 95 test başarılıdır; Ruff, MyPy ve başsız GUI smoke kontrolü de yerelde geçmiştir. Buna karşın ViewModel işlemleri, fazla satış, aynı gün işlem sırası, gerçek Excel round-trip, başarısız yedek sonrası veri silme, migration ve paket oluşturma senaryoları CI kapsamında değildir. Excel testlerinde yoğun `MagicMock` kullanımı gerçek tarih/sütun hatalarını gizlemektedir.
- **Önerilen Çözüm [GPT-5]:** Geçici gerçek SQLite veritabanı kullanan entegrasyon testleri eklenmeli; GUI smoke, MyPy ve paket oluşturma adımları CI'a alınmalı; MyPy zamanla `check_untyped_defs` ve daha sıkı hata denetimine geçirilmelidir.

### 🟡 Sorun #20: Yerel Geliştirme Ortamı ve Bağımlılık Kaynaklarının Dağınıklığı
- **Durum:** Açık
- **Öncelik:** Düşük
- **Açıklama:** Proje Python 3.11+ gerektirirken mevcut `.venv-test` Python 3.9.6 kullanmaktadır ve LibreSSL/urllib3 uyarısı üretmektedir. Runtime ve geliştirme bağımlılıkları hem `requirements.txt` hem `pyproject.toml` içinde tekrarlanmakta; `.coverage` dosyası ignore edilmemektedir.
- **Önerilen Çözüm [GPT-5]:** Yerel ortam Python 3.11/3.12 ile yeniden oluşturulmalı; `pyproject.toml` tek bağımlılık kaynağı yapılmalı veya requirements dosyaları buradan üretilmeli; kullanılmayan doğrudan bağımlılıklar temizlenmeli ve `.coverage` ignore listesine eklenmelidir.

---

## 🧪 3. Kontrol Edilecek Çözümler (Geliştirici Onayı Bekleyenler)
> Agent tarafından kodlaması tamamlanmış, ancak henüz kullanıcı/geliştirici tarafından test edilip onaylanmamış çözümler.
> *Kullanıcı sorunun çözüldüğünü onayladığında ilgili madde bu listeden kaldırılır.*

*(Şu anda onay bekleyen madde bulunmamaktadır.)*

---

## ❌ 4. Reddedilen Öneriler
> Kullanıcı veya geliştirici tarafından uygun görülmeyen ve reddedilen öneriler (Tekrar edilmesini önlemek amacıyla kaydedilir).

*(Henüz reddedilen bir öneri bulunmamaktadır.)*

---

## 🚀 5. Geliştirme ve Özellik Önerileri
> Kullanıcının talebi üzerine proje analiz edilerek çıkarılan mimari, UI/UX ve fonksiyonel geliştirme tavsiyeleri.

- **📊 Temettü Takvimi ve Pasif Gelir Analizi:** Hisselerden elde edilen temettü gelirlerinin yıllık/aylık bazda grafiksel takibi ve temettü verimliliği metrikleri.
- **💼 Çoklu Portföy & İzleme Listesi (Watchlist):** Farklı yatırım stratejileri için ayrı portföyler (örn. Emeklilik, Kısa Vadeli) ve henüz satın alınmamış hisse/fonlar için izleme listeleri.
- **🎨 Dinamik QSS & PyQtGraph Tema Senkronizasyonu:** Koyu/Açık tema değişiminde çizgi ve donut grafiklerinin arka plan ve grid renklerinin otomatik olarak QSS temasına uyum sağlaması.
- **📑 PDF Rapor Dışa Aktarımı & Grafik Araç İpuçları:** Portföy özetlerinin PDF olarak indirilebilmesi ve zaman serisi grafiklerinde fare ile gezinirken detay gösteren tooltip yapısı.
- **🧹 `app/utils/app_settings.py` Temizliği:** Veritabanı `Settings` modeli tarafından karşılanan ve kullanılmayan atıl kodların projeden kaldırılması.
- **📥 Güvenli İçe Aktarım Önizlemesi [GPT-5]:** Excel ve görüntüden aktarımda kaydetmeden önce satır bazlı önizleme, hata açıklaması, mükerrer kayıt tespiti ve tek adımlı geri alma sunulması.
- **💵 Nakit Hesabı ve TWR Analizi [GPT-5]:** Para yatırma/çekme hareketlerinin ayrı kaydedilmesi; nakit akışından arındırılmış zaman-ağırlıklı getiri ile XIRR'ın yan yana gösterilmesi.
- **🕒 Veri Tazeliği ve Kaynak Göstergesi [GPT-5]:** Her fiyat için kaynak, fiyat tarihi, son başarılı yenileme zamanı ve çevrimdışı/önbellekten veri rozeti gösterilmesi.
- **🧾 Lot ve Gerçekleşmiş K/Z Dökümü [GPT-5]:** FIFO/LIFO partilerinin hangi satışlarda tüketildiğini gösteren ayrıntılı lot ekranı ve dönemsel gerçekleşmiş K/Z raporu eklenmesi.
- **🩺 Veritabanı Bakım Ekranı [GPT-5]:** Salt okunur bütünlük kontrolü, yedek doğrulama, yedek listesi, geri yükleme önizlemesi ve taşınabilir yedek dışa aktarımı sunulması.
- **🔐 Bulut Gizliliği ve Finansal Bilgilendirme [GPT-5]:** Bulut sağlayıcısına gönderilen veri kapsamının görünür biçimde açıklanması, ilk kullanım onayı ve öneri ekranlarında bilgilendirme metni bulunması.
- **⌨️ Erişilebilirlik ve Klavye Akışları [GPT-5]:** Tablo/diyalog klavye kısayolları, odak sırası, ekran okuyucu etiketleri, yüksek kontrast kontrolü ve küçük ekranlarda uyarlanabilir yerleşim eklenmesi.

### 🧹 Sadeleştirme ve Kaldırma Önerileri

- **Tek Şema Kaynağı [GPT-5]:** Alembic devreye alındıktan sonra `dump_schema.py` ve elle tutulan `initial.sql` kaldırılmalı veya yalnızca otomatik üretilen dokümantasyon çıktısı haline getirilmelidir.
- **Tek Dokümantasyon ve Bağımlılık Kaynağı [GPT-5]:** Kök README ile `portfolio_tracker/README.md` birleştirilmeli; runtime ve geliştirme bağımlılıklarının çift tanımı kaldırılmalıdır.
- **Kullanılmayan Bağımlılıkların Temizlenmesi [GPT-5]:** Kodda doğrudan kullanılmayan `requests` gibi paketler, dolaylı bağımlılıklar dikkate alınarak proje bağımlılık listesinden çıkarılmalıdır.
- **Değişken Sağlayıcı İddialarının Sadeleştirilmesi [GPT-5]:** Bulut sağlayıcıları için "tamamen ücretsiz" gibi zamanla geçersizleşebilecek ifadeler yerine fiyatlandırma ve kotaların sağlayıcı koşullarına bağlı olduğu belirtilmelidir.
- **Deneysel Özellik İşaretlemesi [GPT-5]:** Temel veri doğruluğu sorunları çözülene kadar asistanın işlem kaydetme ve görüntüden aktarım işlevleri deneysel olarak işaretlenmeli veya özellik bayrağı arkasında tutulmalıdır.
