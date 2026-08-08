# 📌 Portföy Takip ve Analiz Uygulaması — Proje Takip Belgesi

Bu belge aktif işleri, doğrulanmış sorunları, çözüm önerilerini, kullanıcı kontrolü bekleyen değişiklikleri ve geliştirme fikirlerini takip eder.

- **Son güncelleme:** 2026-08-08
- **Aktif sorun sayısı:** 20
- **Kontrol bekleyen çözüm sayısı:** 0

---

## 🧭 0. Takip Standardı ve Sıradaki İşler

### Sıradaki 3 İş

1. **PT-007 — Yedek başarısız olsa bile verilerin silinmesi:** Geri dönüşü olmayan veri kaybı riski nedeniyle ilk sıradadır.
2. **PT-005 — Excel round-trip veri bozulması:** Uygulamanın kendi çıktısının kayıpsız geri alınması sağlanmalıdır.
3. **PT-006 — Geçersiz ve fazla satış işlemleri:** Bütün veri giriş kanalları ortak doğrulamaya bağlanmalıdır.

### Kimlikler

- `TODO-*`: Küçük işler ve notlar
- `PT-*`: Doğrulanacak veya çözülecek sorunlar
- `FTR-*`: Yeni özellik önerileri
- `SIM-*`: Sadeleştirme ve kaldırma önerileri

Kimlikler yeniden numaralandırılmaz ve başka bir madde için tekrar kullanılmaz.

### Standart Durumlar

- **Açık:** Çalışmasına başlanmamış aktif madde
- **Devam Ediyor:** Üzerinde kodlama veya araştırma yapılan madde
- **Engelli:** Dış karar, yetki veya bilgi bekleyen madde
- **Kontrol Bekliyor:** Kodlaması tamamlanmış ve kullanıcı doğrulaması bekleyen madde

### Öncelikler

- **Kritik:** Veri kaybı, veri bozulması veya sır sızıntısı riski
- **Yüksek:** Finansal doğruluğu ya da temel işlevi etkileyen sorun
- **Orta:** Mimari, performans veya kullanıcı deneyimi sorunu
- **Düşük:** Bakım, temizlik veya sınırlı etkili iyileştirme

### Kayıt ve Arşivleme Kuralları

- Yeni sorunlarda kimlik, durum, öncelik, kaynak, tarih, ilgili dosyalar ve kabul kriterleri bulunur.
- Kodlanan çözüm, kimliği korunarak `3. 🧪 Kontrol Edilecek Çözümler` bölümüne taşınır.
- Kullanıcı çözümü onayladığında aktif kayıt kaldırılır; kimlik, tarih ve commit özeti `PROJECT_HISTORY.md` dosyasına eklenir.
- Reddedilen öneriler kimliğiyle birlikte `4. ❌ Reddedilen Öneriler` bölümünde kalır ve tekrar önerilmez.

---

## 📋 1. Yapılacaklar

### TODO-001 — Piyasa Saatlerine Duyarlı Otomatik Yenileme

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** Mevcut kayıt
- **Açıklama:** Mevcut `QTimer` yenilemesi piyasa takvimine ve işlem saatlerine göre yönetilmelidir.
- **Kabul kriterleri:**
  - [ ] Yenileme yalnızca yapılandırılan piyasa saatlerinde otomatik çalışır.
  - [ ] Manuel yenileme piyasa saatinden bağımsız kullanılabilir.

### TODO-002 — Ondalık Basamak Hassasiyeti

- **Durum:** Açık
- **Öncelik:** Düşük
- **Kaynak:** Mevcut kayıt
- **Açıklama:** TEFAS fonları ve küsüratlı lotlar için miktar/fiyat hassasiyeti 4–6 haneye göre ayarlanmalıdır.
- **Kabul kriterleri:**
  - [ ] Giriş, hesaplama ve gösterim katmanları aynı hassasiyet politikasını kullanır.
  - [ ] Yuvarlama nedeniyle portföy toplamında maddi sapma oluşmaz.

### TODO-003 — Veritabanı Composite İndeksleri

- **Durum:** Açık
- **Öncelik:** Düşük
- **Kaynak:** Mevcut kayıt
- **Açıklama:** `transactions` ve `price_history` sorguları için gerekli composite indeksler ölçüm yapılarak belirlenmelidir.
- **Kabul kriterleri:**
  - [ ] İndeks öncesi/sonrası sorgu planı veya süre ölçümü kaydedilir.
  - [ ] İndeksler Alembic migration ile eklenir.

---

## ⚠️ 2. Tespit Edilen Sorunlar ve Çözüm Önerileri

### PT-001 — `datetime.utcnow()` Kullanımı

- **Durum:** Açık
- **Öncelik:** Düşük
- **Kaynak:** Gemini 3.6 Flash
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/models/asset.py`, `app/models/transaction.py`, `app/models/alert.py`
- **Açıklama:** Python 3.12+ ile `datetime.utcnow()` kullanımı amortismana uğramıştır ve timezone bilgisi taşımayan zamanlar üretmektedir.
- **Önerilen çözüm:** `datetime.now(timezone.utc)` veya veritabanı tarafında `func.now()` kullanılmalıdır.
- **Kabul kriterleri:**
  - [ ] Modeller timezone politikasıyla uyumlu tek bir zaman üretim yöntemi kullanır.
  - [ ] Python 3.12 testlerinde ilgili deprecation uyarısı görülmez.

### PT-002 — Loader Thread İçinde ORM Nesnelerinin Paylaşılması

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** Gemini 3.6 Flash
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/viewmodels/portfolio_viewmodel.py`
- **Açıklama:** `PortfolioLoaderThread`, SQLAlchemy oturumuna bağlı `Asset` nesnelerini `ThreadPoolExecutor` worker'larına aktarmaktadır.
- **Önerilen çözüm:** Worker'lara yalnızca `(id, code, asset_type)` gibi ilkel ve immutable veriler gönderilmelidir.
- **Kabul kriterleri:**
  - [ ] Worker fonksiyonları ORM nesnesi veya Session kullanmaz.
  - [ ] Çok varlıklı paralel yenileme testi kararlı biçimde geçer.

### PT-003 — Test Oturumlarında SQLite Kaynak Yönetimi

- **Durum:** Açık
- **Öncelik:** Düşük
- **Kaynak:** Gemini 3.6 Flash
- **Kayıt / son doğrulama:** 2026-08-08 / doğrulama bekliyor
- **İlgili dosyalar:** `tests/conftest.py`, SQLite fixture kullanan test dosyaları
- **Açıklama:** Bazı test fixture'larında Session kapatılsa da Engine dispose edilmediği için kaynak uyarısı riski bulunmaktadır.
- **Önerilen çözüm:** Fixture teardown aşamasında Session kapatılmalı ve Engine dispose edilmelidir.
- **Kabul kriterleri:**
  - [ ] Test paketi kaynak uyarıları hata kabul edilerek çalıştırıldığında başarılıdır.
  - [ ] Tüm geçici Session ve Engine nesneleri teardown sırasında kapatılır.

### PT-004 — Benchmark Servisinde Çevrimdışı Durum Yönetimi

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** Gemini 3.6 Flash
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/services/benchmark_service.py`, `app/views/analytics_view.py`
- **Açıklama:** Benchmark verisi alınamadığında boş sonuç yönetilse de kullanıcıya kaynağın çevrimdışı olduğu açık ve tutarlı biçimde bildirilmelidir.
- **Önerilen çözüm:** Ağ hatası ViewModel tarafından durum nesnesine çevrilmeli ve View yalnızca bu durumu göstermelidir.
- **Kabul kriterleri:**
  - [ ] Çevrimdışı kullanım uygulamayı veya grafiği çökertmez.
  - [ ] Kullanıcı veri bulunmaması ile bağlantı hatasını ayırt edebilir.

### PT-005 — Excel Dışa Aktarımının Güvenli Biçimde Geri Alınamaması

- **Durum:** Açık
- **Öncelik:** Kritik
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/services/import_export_service.py`, `tests/test_import_export.py`
- **Açıklama:** Dışa aktarılan sütun adları içe aktarıcının beklediği adlarla uyuşmamaktadır. Tarihler ORM için normalize edilmemekte ve sayfa bazlı commit işlemleri kısmi aktarım riski oluşturmaktadır. Yeniden üretimde 100,1 TL maliyetli pozisyon 0 TL maliyetle geri alınmıştır.
- **Önerilen çözüm:** Sütunlar kanonik şemaya normalize edilmeli, tüm alanlar doğrulanmalı ve dosyanın tamamı tek transaction içinde işlenmelidir.
- **Kabul kriterleri:**
  - [ ] Uygulamanın kendi Excel çıktısı tüm işlem türleriyle kayıpsız geri alınır.
  - [ ] Hatalı bir satırda hiçbir satır veya varlık veritabanına commit edilmez.
  - [ ] Gerçek SQLite ve gerçek Excel dosyası kullanan round-trip testi geçer.

### PT-006 — Geçersiz ve Portföy Bakiyesini Aşan İşlemler

- **Durum:** Açık
- **Öncelik:** Kritik
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/viewmodels/transaction_viewmodel.py`, `app/viewmodels/ai_viewmodel.py`, `app/services/portfolio_service.py`, `app/services/import_export_service.py`
- **Açıklama:** Manuel, Excel ve asistan kaynaklı işlemler ortak doğrulamadan geçmemektedir. 10 adet varlığa karşı 15 adet satış bakiyeyi `-5` bırakmış ve maliyet yöntemine göre çelişkili kâr üretmiştir.
- **Önerilen çözüm:** Tüm giriş kanallarının kullandığı merkezi, tip tanımlı bir `TransactionService` oluşturulmalıdır.
- **Kabul kriterleri:**
  - [ ] Negatif/sıfır değerler, geçersiz tarih ve fazla satış tüm giriş kanallarında reddedilir.
  - [ ] Aynı doğrulama manuel, Excel, doğal dil ve görüntü aktarımında uygulanır.
  - [ ] WAC/FIFO/LIFO fazla satış testleri aynı hata sonucunu verir.

### PT-007 — Yedek Başarısız Olsa Bile Tüm Verilerin Silinmesi

- **Durum:** Açık
- **Öncelik:** Kritik
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/viewmodels/settings_viewmodel.py`, `app/services/backup_service.py`
- **Açıklama:** `delete_all_data()` yedek sonucunu kontrol etmeden silmeye devam etmektedir. Canlı SQLite dosyası ham dosya kopyasıyla yedeklenmekte ve geri yüklenecek dosyanın bütünlüğü doğrulanmamaktadır.
- **Önerilen çözüm:** SQLite Backup API, bütünlük/şema kontrolü ve atomik restore akışı kullanılmalı; yedek başarısızsa silme durdurulmalıdır.
- **Kabul kriterleri:**
  - [ ] Yedekleme başarısız olduğunda hiçbir kullanıcı verisi silinmez.
  - [ ] Bozuk veya yanlış şemalı dosya aktif veritabanının üzerine yazılmaz.
  - [ ] Başarılı yedek için `quick_check=ok` doğrulanır.

### PT-008 — Gemini API Anahtarının Loglara Sızabilmesi

- **Durum:** Açık
- **Öncelik:** Kritik
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/services/ai/llm_provider.py`, `app/utils/app_settings.py`, `app/views/settings_view.py`
- **Açıklama:** Anahtar URL query parametresiyle gönderildiği için HTTP hata metni üzerinden loglara sızabilir. Anahtar SQLite ayarlarında düz metin tutulmakta ve buluta gönderilen portföy kapsamı için açık onay bulunmamaktadır.
- **Önerilen çözüm:** Anahtar güvenli header ve işletim sistemi anahtar zinciriyle yönetilmeli; loglar maskelenmeli ve ilk kullanım onayı alınmalıdır.
- **Kabul kriterleri:**
  - [ ] Hata logları ve kullanıcı mesajları API anahtarını içermez.
  - [ ] Anahtar `portfolio.db` veya yedeklerinde düz metin bulunmaz.
  - [ ] Bulut sağlayıcısı etkinleştirilmeden önce veri kapsamı onaylanır.

### PT-009 — Performans ve K/Z Yüzdelerinin Yanıltıcı Olabilmesi

- **Durum:** Açık
- **Öncelik:** Yüksek
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/viewmodels/portfolio_viewmodel.py`, `app/viewmodels/analytics_viewmodel.py`, `app/services/portfolio_service.py`, `app/services/snapshot_service.py`
- **Açıklama:** Snapshot değişimleri nakit akışlarından arındırılmadığı için yeni alımlar performans gibi ölçülmektedir. Toplam K/Z yüzdesi de kapatılmış pozisyon kârını yalnızca açık pozisyon maliyetine bölebilmektedir.
- **Önerilen çözüm:** Nakit hareketleri ayrı tutulmalı, TWR eklenmeli ve gerçekleşmiş/açık/toplam dönem getirileri ayrıştırılmalıdır.
- **Kabul kriterleri:**
  - [ ] Para yatırma veya çekme, fiyatlar değişmediğinde TWR'ı değiştirmez.
  - [ ] K/Z metriklerinin pay ve paydası arayüzde açıklanır.
  - [ ] Kapatılmış pozisyonlar toplam getiri yüzdesini yapay biçimde büyütmez.

### PT-010 — XIRR Hesabının Yakınsamayan Sonucu Geçerli Kabul Etmesi

- **Durum:** Açık
- **Öncelik:** Yüksek
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/services/portfolio_service.py`, `tests/test_portfolio_service.py`
- **Açıklama:** Newton-Raphson yakınsamadığında son tahmin döndürülmektedir. Tek işaretli nakit akışları yaklaşık `1.98e277` gibi anlamsız sonuç üretebilmektedir.
- **Önerilen çözüm:** İşaret kontrolü yapılmalı, güvenli aralıklı kök bulma kullanılmalı ve yakınsamama ayrı sonuç olarak modellenmelidir.
- **Kabul kriterleri:**
  - [ ] Tek işaretli nakit akışı `hesaplanamadı` sonucu verir.
  - [ ] Bilinen -1000/+1100 yıllık örneği yaklaşık %10 verir.
  - [ ] Sonlu olmayan veya aşırı büyük değer arayüze ulaşmaz.

### PT-011 — Aynı Günlü İşlemlerin Belirsiz Sıralanması

- **Durum:** Açık
- **Öncelik:** Yüksek
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/services/portfolio_service.py`, `app/models/transaction.py`
- **Açıklama:** Maliyet hesabı yalnızca tarihe göre sıralandığından aynı günlü işlemlerin sonucu veritabanı dönüş sırasına bağlı kalabilir.
- **Önerilen çözüm:** En az `(date, id)` sırası kullanılmalı; gerekirse gün içi `sequence` veya işlem zamanı alanı eklenmelidir.
- **Kabul kriterleri:**
  - [ ] Aynı veri farklı sorgu sıralarında aynı maliyet/K/Z sonucunu verir.
  - [ ] Aynı gün alım, satış ve split sırası testlerle tanımlanır.

### PT-012 — Manuel Yenilemenin Önbelleği Atlamaması

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/views/main_window.py`, `app/viewmodels/portfolio_viewmodel.py`
- **Açıklama:** `Şimdi Yenile` butonu varsayılan `load_data()` çağrısını yaptığı için 15 dakika içinde eski fiyatı gösterebilir.
- **Önerilen çözüm:** Manuel akış `force_refresh=True` kullanmalı ve yükleme sırasında biriken zorunlu yenileme isteği korunmalıdır.
- **Kabul kriterleri:**
  - [ ] Manuel yenileme her fiyat servisinde cache bypass eder.
  - [ ] Yükleme sürerken basılan manuel yenileme tamamlanınca zorunlu olarak çalışır.

### PT-013 — TEFAS İstek Sınırının Paralel Çağrılarda Uygulanmaması

- **Durum:** Açık
- **Öncelik:** Yüksek
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/services/tefas_service.py`, `app/viewmodels/portfolio_viewmodel.py`
- **Açıklama:** Her worker'ın ayrı 500 ms beklemesi isteklerin eşzamanlı gönderilmesini engellemez; paylaşılan `Crawler` nesnesi de eşzamanlı kullanılmaktadır.
- **Önerilen çözüm:** Süreç genelinde kilitli rate limiter kullanılmalı; crawler erişimi seri veya izole hale getirilmelidir.
- **Kabul kriterleri:**
  - [ ] Ardışık TEFAS istek başlangıçları arasında en az 500 ms bulunur.
  - [ ] Aynı crawler birden fazla thread tarafından eşzamanlı kullanılmaz.

### PT-014 — Veritabanı Migration ve Foreign Key Kontrolünün Olmaması

- **Durum:** Açık
- **Öncelik:** Yüksek
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/database/engine.py`, `app/database/migrations/initial.sql`, `pyproject.toml`
- **Açıklama:** `create_all()` mevcut tabloları yükseltmez. Alembic bağımlılığı olmasına rağmen migration zinciri yoktur ve foreign key kontrolü açıkça etkinleştirilmemiştir.
- **Önerilen çözüm:** Sürümlü Alembic migration'ları oluşturulmalı; migration öncesi yedek alınmalı ve SQLite bağlantı pragma'ları merkezi uygulanmalıdır.
- **Kabul kriterleri:**
  - [ ] Önceki şemadaki örnek veritabanı veri kaybı olmadan güncellenir.
  - [ ] Her uygulama bağlantısında `PRAGMA foreign_keys=ON` doğrulanır.
  - [ ] Migration hatasında aktif veritabanı geri alınabilir kalır.

### PT-015 — Paketleme Yapılandırmasının Temiz Klonda Çalışmaması

- **Durum:** Açık
- **Öncelik:** Yüksek
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `pyproject.toml`, `.gitignore`, `portfolio_tracker.spec`, `main.py`
- **Açıklama:** Alt paketler ve kaynak dosyaları kurulabilir pakete eksik girebilir. PyInstaller spec dosyası ignore edildiğinden README komutu temiz klonda tekrarlanamaz.
- **Önerilen çözüm:** Package discovery/package-data tamamlanmalı, spec dosyası izlenmeli ve paket smoke testi CI'a eklenmelidir.
- **Kabul kriterleri:**
  - [ ] Temiz klondan wheel ve hedef platform paketi oluşturulur.
  - [ ] Paket açıldığında ikon, font, QSS ve tüm alt modüller bulunur.
  - [ ] Kurulan `portfolio-tracker` giriş noktası uygulamayı başlatır.

### PT-016 — UI Thread'ini Donduran İşlemler ve Eksik Worker Kapanışı

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/views/settings_view.py`, `app/viewmodels/portfolio_viewmodel.py`, `app/views/main_window.py`
- **Açıklama:** Sağlayıcı bağlantı testi ve yüzdelik içe aktarım ana UI thread'inde ağ çağrısı yapabilir. Ana pencere kapanırken portföy loader için kontrollü iptal/bekleme yoktur.
- **Önerilen çözüm:** Uzun işlemler ViewModel worker'larına taşınmalı; ilerleme, iptal ve kapanış protokolü eklenmelidir.
- **Kabul kriterleri:**
  - [ ] Ağ zaman aşımında pencere etkileşime açık kalır.
  - [ ] Yenileme sırasında uygulama kapatıldığında çalışan thread uyarısı veya çökme oluşmaz.

### PT-017 — View Katmanındaki Doğrudan Servis Bağımlılıkları

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/views/analytics_view.py`, `app/views/settings_view.py`, `app/views/ai_assistant_view.py`
- **Açıklama:** View dosyaları benchmark, hesaplama, sağlayıcı ve analiz servislerine doğrudan erişmektedir.
- **Önerilen çözüm:** Servis çağrıları ve asenkron iş yönetimi ilgili ViewModel'lere taşınmalıdır.
- **Kabul kriterleri:**
  - [ ] View modülleri Model veya service modüllerini doğrudan import etmez.
  - [ ] View yalnızca ViewModel sinyalleri ve render verisiyle çalışır.

### PT-018 — Önbellek Sürelerinin Dokümantasyonla Uyuşmaması

- **Durum:** Açık
- **Öncelik:** Düşük
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `app/utils/cache.py`, `app/services/currency_service.py`, `app/services/benchmark_service.py`, `app/services/tefas_service.py`
- **Açıklama:** Kur, benchmark ve fon adı belgelenen farklı süreler yerine ortak 15 dakikalık TTL kullanmaktadır.
- **Önerilen çözüm:** Cache kayıtları anahtar bazlı TTL kabul etmeli ve süreler teknik spesifikasyonla eşleşmelidir.
- **Kabul kriterleri:**
  - [ ] Fiyat, kur, benchmark ve fon adı için ayrı TTL testleri bulunur.
  - [ ] Kod yorumları, teknik belge ve çalışma zamanı aynı süreleri gösterir.

### PT-019 — Test ve CI Kapsamının Kritik Akışları İçermemesi

- **Durum:** Açık
- **Öncelik:** Orta
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `.github/workflows/ci.yml`, `tests/`, `smoke_test.py`, `pyproject.toml`
- **Açıklama:** 95 test, Ruff, MyPy ve yerel GUI smoke kontrolü başarılıdır; ancak gerçek Excel round-trip, fazla satış, yedek başarısızlığı, migration, ViewModel ve paketleme akışları CI'da yoktur.
- **Önerilen çözüm:** Gerçek geçici SQLite kullanan entegrasyon testleri ile GUI smoke, MyPy ve paketleme adımları CI'a eklenmelidir.
- **Kabul kriterleri:**
  - [ ] PT-005, PT-006 ve PT-007 için gerçek entegrasyon testleri bulunur.
  - [ ] CI test, Ruff, MyPy, GUI smoke ve paket smoke adımlarını çalıştırır.

### PT-020 — Geliştirme Ortamı ve Bağımlılık Kaynaklarının Dağınıklığı

- **Durum:** Açık
- **Öncelik:** Düşük
- **Kaynak:** GPT-5
- **Kayıt / son doğrulama:** 2026-08-08 / 2026-08-08
- **İlgili dosyalar:** `pyproject.toml`, `requirements.txt`, `.gitignore`, `.venv-test/`
- **Açıklama:** Proje Python 3.11+ isterken yerel test ortamı Python 3.9.6 kullanmaktadır. Bağımlılıklar iki dosyada tekrarlanmakta ve `.coverage` ignore edilmemektedir.
- **Önerilen çözüm:** Ortam 3.11/3.12 ile yenilenmeli, tek bağımlılık kaynağı belirlenmeli ve çalışma çıktıları ignore edilmelidir.
- **Kabul kriterleri:**
  - [ ] Yerel test ortamı desteklenen Python sürümünü kullanır.
  - [ ] Runtime ve geliştirme bağımlılıklarının tek yetkili kaynağı vardır.
  - [ ] Test çıktıları çalışma ağacında izlenmeyen dosya bırakmaz.

---

## 🧪 3. Kontrol Edilecek Çözümler

> Kodlaması tamamlanan madde, kullanıcı doğrulamasına kadar özgün `PT-*` kimliğiyle burada tutulur. Test adımları ve commit kimliği mutlaka yazılır.

*(Şu anda kontrol bekleyen çözüm bulunmamaktadır.)*

---

## ❌ 4. Reddedilen Öneriler

> Reddedilen madde kimliği, gerekçesi ve karar tarihiyle burada tutulur.

*(Henüz reddedilen öneri bulunmamaktadır.)*

---

## 🚀 5. Geliştirme ve Özellik Önerileri

- **FTR-001 — Temettü Takvimi ve Pasif Gelir Analizi** — **Kaynak:** Mevcut kayıt — Temettü gelirlerinin aylık/yıllık takibi ve temettü verimliliği metrikleri.
- **FTR-002 — Çoklu Portföy ve İzleme Listesi** — **Kaynak:** Mevcut kayıt — Farklı yatırım stratejileri için ayrı portföyler ve henüz alınmamış varlıklar için izleme listesi.
- **FTR-003 — Dinamik QSS ve Grafik Tema Senkronizasyonu** — **Kaynak:** Mevcut kayıt — Tema değişiminde PyQtGraph ve QtCharts renklerinin QSS ile tam senkronizasyonu.
- **FTR-004 — PDF Rapor ve Grafik Araç İpuçları** — **Kaynak:** Mevcut kayıt — Portföy özetinin PDF çıktısı ve zaman serilerinde hover tooltip desteği.
- **FTR-005 — `app_settings.py` Temizliği** — **Kaynak:** Mevcut kayıt — Kullanılmayan ayar yardımcılarının tespit edilip kaldırılması.
- **FTR-006 — Güvenli İçe Aktarım Önizlemesi** — **Kaynak:** GPT-5 — Satır bazlı önizleme, hata açıklaması, mükerrer kayıt tespiti ve tek adımlı geri alma.
- **FTR-007 — Nakit Hesabı ve TWR Analizi** — **Kaynak:** GPT-5 — Para yatırma/çekme hareketleri ve nakit akışından arındırılmış zaman-ağırlıklı getiri.
- **FTR-008 — Veri Tazeliği ve Kaynak Göstergesi** — **Kaynak:** GPT-5 — Fiyat kaynağı, fiyat tarihi, son başarılı yenileme ve çevrimdışı/önbellek rozeti.
- **FTR-009 — Lot ve Gerçekleşmiş K/Z Dökümü** — **Kaynak:** GPT-5 — FIFO/LIFO partilerinin satışlarla eşleşmesini gösteren ayrıntılı rapor.
- **FTR-010 — Veritabanı Bakım Ekranı** — **Kaynak:** GPT-5 — Bütünlük kontrolü, yedek doğrulama, geri yükleme önizlemesi ve taşınabilir yedek.
- **FTR-011 — Bulut Gizliliği ve Finansal Bilgilendirme** — **Kaynak:** GPT-5 — Gönderilen veri kapsamı, ilk kullanım onayı ve öneri ekranı bilgilendirmesi.
- **FTR-012 — Erişilebilirlik ve Klavye Akışları** — **Kaynak:** GPT-5 — Kısayollar, odak sırası, ekran okuyucu etiketleri, kontrast ve küçük ekran uyumu.

### Sadeleştirme ve Kaldırma Önerileri

- **SIM-001 — Tek Şema Kaynağı** — **Kaynak:** GPT-5 — Alembic devreye alındıktan sonra `dump_schema.py` ve elle tutulan `initial.sql` kaldırılmalı veya otomatik çıktı olmalıdır.
- **SIM-002 — Tek Dokümantasyon ve Bağımlılık Kaynağı** — **Kaynak:** GPT-5 — İki README birleştirilmeli; runtime ve geliştirme bağımlılıklarının çift tanımı kaldırılmalıdır.
- **SIM-003 — Kullanılmayan Bağımlılıkların Temizlenmesi** — **Kaynak:** GPT-5 — Kodda doğrudan kullanılmayan `requests` gibi bağımlılıklar doğrulanarak kaldırılmalıdır.
- **SIM-004 — Değişken Sağlayıcı İddialarının Sadeleştirilmesi** — **Kaynak:** GPT-5 — "Tamamen ücretsiz" yerine fiyatlandırma ve kotaların sağlayıcı koşullarına bağlı olduğu belirtilmelidir.
- **SIM-005 — Deneysel Özellik İşaretlemesi** — **Kaynak:** GPT-5 — Temel veri doğruluğu düzelene kadar asistanın işlem kaydetme ve görüntü aktarımı deneysel işaretlenmelidir.
