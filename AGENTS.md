# Kişisel Yatırım Portföyü Takip ve Analiz Uygulaması — Geliştirici Talimatı

## Rol

Sen kıdemli bir yazılım mimarı, finansal veri analisti ve UI/UX tasarımcısısın. Benim için kişisel bir "Yatırım Portföyü Takip ve Analiz" masaüstü uygulaması geliştireceksin. Uygulama yalnızca kişisel kullanım içindir, sunucu bileşeni yoktur. Tüm veri kullanıcının makinesinde tutulur.

## Kapsam ve Varlık Türleri

Uygulama iki varlık sınıfını destekleyecek:

1. **BIST Hisse Senetleri** (Borsa İstanbul'da işlem gören pay senetleri)
2. **TEFAS Yatırım Fonları** (Türkiye Elektronik Fon Alım Satım Platformu'nda işlem gören yatırım fonları)

Veri modeli `asset_type` alanıyla ayrılacak biçimde tasarlanmalı, gelecekte kripto/emtia/döviz gibi sınıfların eklenebileceği şekilde genişletilebilir kalmalı; ancak ilk sürümde yalnızca BIST ve TEFAS aktif ve tam fonksiyonel olacak.

## Zorunlu Teknoloji Yığını (Tech Stack)

Model kendi seçim yapmayacak; aşağıdaki yığın sabittir:

- **Dil:** Python 3.11 veya üzeri
- **GUI Çerçevesi (framework):** PySide6 (Qt6 Python binding'i, LGPL lisanslı)
- **Mimari (architecture):** MVVM (Model–View–ViewModel), View ve Model kesinlikle doğrudan bağlanmayacak, araya ViewModel katmanı girecek
- **Veritabanı:** SQLite (yerel dosya, `data/portfolio.db`)
- **ORM:** SQLAlchemy 2.x (Core + ORM)
- **Grafikler:** PyQtGraph (performanslı çizimler ve tarihsel çizgi grafikler için) + QtCharts (pasta/donut grafikler için)
- **İkonlar:** qtawesome (Font Awesome ikon seti)
- **Tipografi:** Inter (ana metin) + JetBrains Mono (sayısal değerler ve kodlar)
- **Animasyon:** `QPropertyAnimation` ve `QGraphicsOpacityEffect`
- **HTTP istekleri:** `httpx` (eşzamansız destekli)
- **Veri çekme kütüphaneleri:** `tefas-crawler` (TEFAS için), `yfinance` (BIST için), `requests` (TCMB XML için)
- **Excel/CSV:** `openpyxl` ve `pandas`
- **Paketleme:** PyInstaller (macOS `.dmg` ve Windows `.exe` üretimi)
- **Loglama:** Python standart `logging` modülü, `RotatingFileHandler` ile
- **Bildirim:** `plyer` (cross-platform native notification)

Cross-platform uyumluluk: macOS (Intel + Apple Silicon) ve Windows 10/11 doğrulanmış olmalı.

## Klasör Yapısı

```
portfolio_tracker/
├── main.py
├── requirements.txt
├── README.md
├── app/
│   ├── __init__.py
│   ├── config.py                    # Sabitler, renk paleti, yollar
│   ├── resources/
│   │   ├── fonts/                   # Inter, JetBrains Mono
│   │   ├── icons/
│   │   └── styles/
│   │       ├── light.qss
│   │       └── dark.qss
│   ├── models/                      # Veri modelleri (SQLAlchemy ORM)
│   │   ├── asset.py
│   │   ├── transaction.py
│   │   ├── price_history.py
│   │   ├── alert.py
│   │   └── settings.py
│   ├── services/                    # Dış dünyayla konuşan katman
│   │   ├── tefas_service.py
│   │   ├── bist_service.py
│   │   ├── currency_service.py      # TCMB USD/TRY
│   │   ├── portfolio_service.py     # İş mantığı (ortalama maliyet, K/Z, XIRR)
│   │   ├── import_export_service.py
│   │   └── backup_service.py
│   ├── viewmodels/                  # UI state ve bind katmanı
│   │   ├── portfolio_viewmodel.py
│   │   ├── transaction_viewmodel.py
│   │   ├── analytics_viewmodel.py
│   │   └── settings_viewmodel.py
│   ├── views/                       # PySide6 widget'ları
│   │   ├── main_window.py
│   │   ├── dashboard_view.py
│   │   ├── portfolio_view.py
│   │   ├── transactions_view.py
│   │   ├── analytics_view.py
│   │   ├── alerts_view.py
│   │   ├── settings_view.py
│   │   └── widgets/                 # KPI kartı, grafik widget'ları vb.
│   ├── database/
│   │   ├── engine.py
│   │   ├── session.py
│   │   └── migrations/
│   └── utils/
│       ├── formatters.py            # Para birimi, yüzde, tarih formatlaması
│       ├── logger.py
│       └── cache.py                 # Fiyat önbelleği (price cache)
├── data/                            # .gitignore içinde
│   ├── portfolio.db
│   └── backups/
├── logs/
└── tests/
    ├── test_portfolio_service.py
    ├── test_tefas_service.py
    └── test_import_export.py
```

## Veritabanı Şeması (SQLite)

Aşağıdaki tabloları SQLAlchemy ORM ile tanımla; Alembic migration zorunlu değil fakat `database/migrations/initial.sql` olarak ilk şema SQL'i dosyaya yaz.

**`assets` tablosu** — Varlık tanımları
- `id` (PK), `code` (unique, örn: `THYAO` veya `AFT`), `name`, `asset_type` (enum: `BIST`, `TEFAS`), `currency` (varsayılan `TRY`), `created_at`, `updated_at`

**`transactions` tablosu** — İşlem geçmişi
- `id` (PK), `asset_id` (FK → assets), `transaction_type` (enum: `BUY`, `SELL`), `date` (DATE), `quantity` (DECIMAL, TEFAS için adet sayısal), `unit_price` (DECIMAL), `commission` (DECIMAL, varsayılan 0), `tax` (DECIMAL, varsayılan 0; TEFAS stopajı için), `note` (TEXT, opsiyonel), `created_at`

**`price_history` tablosu** — Tarihsel fiyat kayıtları (grafikler için)
- `id` (PK), `asset_id` (FK), `date` (DATE), `close_price` (DECIMAL), UNIQUE(`asset_id`, `date`)

**`portfolio_snapshots` tablosu** — Portföyün günlük toplam değeri (zaman serisi grafikleri için)
- `id` (PK), `date` (DATE, UNIQUE), `total_value_try`, `total_value_usd`, `total_cost_try`, `unrealized_pnl_try`

**`alerts` tablosu** — Uyarılar
- `id` (PK), `asset_id` (FK), `alert_type` (enum: `PRICE_ABOVE`, `PRICE_BELOW`, `PCT_CHANGE_ABOVE`, `PCT_CHANGE_BELOW`), `threshold` (DECIMAL), `is_active` (BOOL), `triggered_at` (nullable), `created_at`

**`settings` tablosu** — Anahtar-değer çifti olarak tek satırlı ayar tablosu
- `key` (PK), `value` (TEXT)
- Saklanacak anahtarlar: `theme` (`system`/`light`/`dark`), `default_currency` (`TRY`/`USD`), `refresh_interval_minutes`, `cost_method` (`WAC`/`FIFO`/`LIFO`), `notifications_enabled`, `language` (`tr`/`en`), `last_backup_date`

## Ortalama Maliyet ve K/Z Hesaplama

- Ortalama maliyet (average cost), varsayılan olarak **Ağırlıklı Ortalama — WAC (Weighted Average Cost)** yöntemi ile hesaplanacak. Ayarlardan **FIFO (First-In, First-Out)** veya **LIFO (Last-In, First-Out)** olarak değiştirilebilir olmalı.
- **Gerçekleşmiş K/Z (Realized P/L):** Satılan pozisyonların kârı/zararı. Satış anındaki ortalama maliyete göre hesaplanır ve `transactions` tablosundan türetilir.
- **Gerçekleşmemiş K/Z (Unrealized P/L):** Hâlâ portföyde tutulan pozisyonların güncel fiyatla ortalama maliyet arasındaki farkı.
- Her iki değer ayrı sütunlar/kartlar olarak gösterilecek.
- Komisyon ve vergi toplam maliyete eklenecek (alım komisyonu maliyeti yükseltir; satış komisyonu ve stopaj gerçekleşen kâr düşer).

## Veri Kaynakları ve Servis Detayları

**TEFAS servisi (`tefas_service.py`):**
- `tefas-crawler` kütüphanesini kullan. Fonun güncel fiyatı için `Crawler().fetch(start, end, name)` kullanımı temel alınmalı.
- Rate limit olmaması için istek aralığı 500ms.
- Başarısız çağrılarda 3 kez üstel geri çekilme (exponential backoff).

**BIST servisi (`bist_service.py`):**
- `yfinance` kullan. Hisse kodu `THYAO.IS` formatında. Tarihsel veri için `yf.Ticker("THYAO.IS").history(period="1y")`.
- Yedek kaynak olarak `isyatirim.com.tr` HTML scraping hazır tutulacak (TODO bırakabilirsin, ilk sürümde implement etme).

**Döviz servisi (`currency_service.py`):**
- TCMB resmi XML endpoint: `https://www.tcmb.gov.tr/kurlar/today.xml`. Günlük tek istek, sonuç 24 saat cache'lenmeli.
- USD/TRY çapraz kuru portföy USD cinsinden görüntülendiğinde kullanılacak.

**Fiyat önbelleği:** Aynı varlık için 15 dakika içinde tekrar istek atılmamalı (`utils/cache.py`). Kullanıcı "Şimdi Yenile" dediğinde cache bypass edilir.

## UI / UX Tasarım Sistemi

**Renk Paleti:**

| Rol | Açık Tema | Koyu Tema |
|---|---|---|
| Ana vurgu (Türk Kırmızısı) | `#E30A17` | `#E30A17` |
| İkincil vurgu (Turkuaz) | `#00B5E2` | `#00B5E2` |
| Arka plan | `#F8F9FA` | `#0F1115` |
| Yüzey/Kart | `#FFFFFF` | `#1A1D23` |
| Kenarlık | `#E5E7EB` | `#2A2F38` |
| Birincil metin | `#111827` | `#E5E7EB` |
| İkincil metin | `#6B7280` | `#9CA3AF` |
| **Kâr (positive)** | `#10B981` | `#10B981` |
| **Zarar (negative)** | `#B91C1C` | `#DC2626` |
| Nötr | `#6B7280` | `#9CA3AF` |

**Kritik Kural:** Türk kırmızısı (`#E30A17`) yalnızca UI vurgu/aksan rengi olarak kullanılacak (aktif sekme, vurgulanmış buton, logo aksan çizgisi vb.). Kâr/zarar gösterimlerinde asla kırmızı vurgu rengi kullanılmayacak. Zarar için koyu vişne (`#B91C1C`), kâr için zümrüt yeşili (`#10B981`) kullanılacak — bu renkler ana vurgu rengiyle karıştırılmayacak.

**Tema Yönetimi:** Sistem temasına uyum varsayılan. Kullanıcı ayar ekranından `system`/`light`/`dark` arasında seçebilmeli. Tema değişikliği anında uygulanır, yeniden başlatma gerektirmez. Tüm stiller `app/resources/styles/` altında `.qss` dosyalarında tanımlanır.

**Navigasyon:** Sol tarafta dikey sidebar. Sekmeler (yukarıdan aşağıya): Dashboard, Portföy, İşlemler, Analiz, Uyarılar, Ayarlar. Aktif sekme Türk kırmızısı çizgi vurgusuyla işaretlenir.

**Animasyonlar:** Sekme geçişlerinde 200ms fade-in. KPI kartlarında değer değişirken 400ms yumuşak sayaç animasyonu (number count-up). Grafiklerin ilk çiziminde sol-sağ soldan-sağa çizim animasyonu.

## Ekranlar

### 1. Dashboard

Üstte 4 KPI kartı (yatay), altta 2 grafik (yan yana), en altta "Son 5 işlem" listesi.

**KPI Kartları:**
1. **Toplam Portföy Değeri** — TL ve USD, küçük trendik (sparkline son 30 gün)
2. **Bugünkü Değişim** — TL ve yüzde, renkli (kâr/zarar)
3. **Toplam K/Z** — gerçekleşmiş + gerçekleşmemiş birleşik, yüzde ile
4. **En İyi / En Kötü Pozisyon** — tek kartta üstte en iyi, altta en kötü

**Grafikler:**
- Sol: **Varlık sınıfı dağılımı** (donut grafik — BIST %X, TEFAS %Y)
- Sağ: **Portföy değeri zaman serisi** (son 90 gün çizgi grafik)

### 2. Portföy

Ana tablo. Sütunlar:

| # | Kod | Ad | Tür | Adet | Ort. Maliyet | Güncel Fiyat | Toplam Maliyet | Güncel Değer | Günlük Değ. | Toplam K/Z | K/Z % | Portföy % |

Özellikler:
- Tıklanabilir sütun başlıkları ile sıralama
- Sağ tık menüsü: Düzenle, İşlem Ekle, Sil, Grafiği Aç
- Üstte arama kutusu ve varlık tipi filtresi
- Alt bilgi satırı: toplam satır sayısı, toplam değer
- "+ Varlık Ekle" butonu (Türk kırmızısı, sağ üst)
- "Fiyatları Yenile" butonu (sağ üst, yanında son güncelleme zaman damgası)

### 3. İşlemler

Tüm işlem geçmişi kronolojik sırada. Sütunlar: Tarih, Varlık, Tür (Alım/Satım), Adet, Birim Fiyat, Komisyon, Vergi, Toplam, Not.

Filtreler: Tarih aralığı, varlık, işlem tipi. "+ Yeni İşlem" butonu ile alım/satım kaydı girme. Düzenleme ve silme desteği.

### 4. Analiz

**Üst sekmeler:** Performans / Dağılım / Karşılaştırma

**Performans sekmesi:**
- Zaman serisi grafiği: Portföy değeri vs. Toplam yatırılan sermaye (cost basis) — iki çizgi
- Tarih aralığı butonları: 1H / 1A / 3A / 6A / YBB (YTD) / 1Y / Tümü
- Metrik kutucukları: **XIRR (yıllık para-ağırlıklı getiri)**, **Sharpe Oranı**, **Maksimum Düşüş (Max Drawdown)**, **Volatilite (yıllık standart sapma)**

**Dağılım sekmesi:**
- Pasta grafik 1: Varlık sınıfına göre (BIST vs TEFAS)
- Pasta grafik 2: Bireysel varlık kodlarına göre
- Çubuk grafik: Her varlığın toplam katkısı (TL)

**Karşılaştırma sekmesi (Benchmark):**
- Çok şeritli (multi-series) çizgi grafik. Aynı grafikte portföy değeri + BIST 100 endeksi + TÜFE (enflasyon) + USD/TRY + altın gram fiyatı. Kullanıcı overlay'ları aç/kapa yapabilir.
- Başlangıç tarihi normalize edilir (tüm seriler 100'den başlar), böylece yüzde bazlı kıyaslama mümkün olur.

### 5. Uyarılar

Tanımlı uyarı listesi + "+ Yeni Uyarı" butonu. Uyarı tipleri: fiyat üstü, fiyat altı, yüzde değişim üstü, yüzde değişim altı. Tetiklenen uyarılar native OS bildirimi olarak gelir (`plyer`).

### 6. Ayarlar

- Tema (System / Light / Dark)
- Varsayılan para birimi (TRY / USD)
- Fiyat yenileme sıklığı (15 / 30 / 60 dk, veya Manuel)
- Ortalama maliyet yöntemi (WAC / FIFO / LIFO)
- Bildirim açık/kapalı
- Dil (TR / EN) — opsiyonel, TR varsayılan
- **Veri Yönetimi alt bölümü:** Yedek oluştur, yedekten geri yükle, tüm veriyi sil
- **Hakkında** bölümü: Sürüm, geliştirici, lisans

## İçe ve Dışa Aktarma (Import / Export)

**Dışa aktarma (Excel `.xlsx` ve CSV):**
- Portföy durumu (tam sütunlu)
- İşlem geçmişi (tam)
- Kullanıcı hangi sütunların dahil edileceğini seçebilir (checkbox listesi)

**İçe aktarma (Excel ve CSV):**
Uygulama aşağıdaki formatların **hepsini** otomatik tanıyıp işleyebilmeli:

| Senaryo | Gereken sütunlar |
|---|---|
| Minimum (yüzdelik) | `kod`, `yüzde` |
| Adet + maliyet | `kod`, `adet`, `ortalama_maliyet` |
| Tam işlem geçmişi | `tarih`, `kod`, `tür`, `adet`, `birim_fiyat`, `komisyon` |

Import akışı:
1. Kullanıcı dosyayı seçer
2. Uygulama sütunları otomatik tespit eder; belirsizlikte mapping ekranı açılır
3. Önizleme tablosunda kullanıcı verileri onaylar
4. Onay sonrası varlıklar eklenir, güncel fiyatlar otomatik çekilir
5. "Yüzdelik" senaryosunda kullanıcıdan toplam portföy değeri girmesi istenir; adetler oradan hesaplanır

## Fiyat Yenileme ve Zamanlayıcı

- Uygulama açılışta ve ayarlanan aralıkta (15/30/60 dk) otomatik fiyat yenilemesi yapar
- Yenileme arka planda `QThread` içinde çalışır; UI asla donmaz
- Yenileme sırasında sidebar altında küçük dönen gösterge
- Başarısız istekler log'a yazılır, kullanıcı UI'da sessiz kalmış varlıkları görebilir

## Yedekleme

- Her uygulama açılışında, son yedekten 7 gün geçtiyse otomatik yedek alınır
- Yedek konumu: `data/backups/backup_YYYYMMDD_HHMMSS.db`
- Son 10 yedek saklanır, eskisi silinir
- Manuel yedek alma ve dışa aktarma Ayarlar'dan yapılabilir

## Loglama

- `logs/app.log` — genel uygulama logu
- `logs/prices.log` — fiyat çekme istekleri
- `RotatingFileHandler` ile dosya başına 5MB, 5 rotasyon
- Seviye: Geliştirmede DEBUG, production'da INFO

## Paketleme

- PyInstaller `.spec` dosyaları hem macOS hem Windows için hazırlanacak
- macOS çıktısı: `PortfolioTracker.dmg` (universal binary, Intel + Apple Silicon)
- Windows çıktısı: `PortfolioTracker-Setup.exe` (NSIS veya Inno Setup ile installer tercih edilir; minimum `.exe` tek dosya da olur)
- Uygulama ikonu: hem `.icns` (macOS) hem `.ico` (Windows) sağlanacak; prompt sonunda placeholder kabul edilir

## Test

- `tests/` klasöründe `pytest` ile:
  - `portfolio_service` için ortalama maliyet (WAC/FIFO/LIFO), realized/unrealized P/L birim testleri
  - `import_export_service` için en az 3 örnek Excel dosyasıyla import parse testi
  - Mock'lanmış TEFAS ve BIST servisleri
- Minimum kapsama (coverage) hedefi servis katmanında %70

## Kod Kalitesi

- Tür ipuçları (type hints) her fonksiyonda zorunlu
- Docstring'ler Google stiliyle
- `black` ile formatla, `ruff` ile lint
- Servis katmanında asla doğrudan print — her şey `logger` üzerinden

## Çıktı Formatı — ÖNEMLİ

**Kodu tek bir devasa dosya olarak verme.** Çalışma sırasını şu şekilde izle:

**Adım 0 —** Önce seçtiğin teknolojileri, klasör yapısını, veritabanı şemasını ve kritik mimari kararları özetle. Bu özet onayım için sunulmalı, fakat sen kodu beklemeden başlayabilirsin.

**Adım 1 —** `requirements.txt` ve proje iskeletini oluştur.

**Adım 2 —** Veritabanı katmanı: modeller, engine, session, migration SQL.

**Adım 3 —** Servis katmanı: TEFAS, BIST, currency, portfolio, import/export, backup. Her servis için mock'lu birim test.

**Adım 4 —** ViewModel katmanı.

**Adım 5 —** UI — sırasıyla: Ana pencere + sidebar → Dashboard → Portföy → İşlemler → Analiz → Uyarılar → Ayarlar.

**Adım 6 —** Tema sistemi ve `.qss` stilleri.

**Adım 7 —** Paketleme (.spec dosyaları) ve README.

Her adımda ilgili dosyaları tam içerikle yaz. Adım geçişlerinde kısa bir özet ver: ne yazıldı, ne sıradaki adım.

## Beklenti

Bu uygulama tek bir geliştirici (ben) tarafından kişisel olarak kullanılacak. Güzel olması değil, **doğru çalışması** ve **verinin güvende olması** öncelikli. Kod okunabilir, modüler ve genişletilebilir olmalı. Şık tasarım önemli ama asla fonksiyonellik pahasına değil. Şüpheye düştüğün yerde **yorum satırında belirt ve varsayım yap**, durma.
