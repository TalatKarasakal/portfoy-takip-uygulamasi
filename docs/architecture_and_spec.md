# Kişisel Yatırım Portföyü Takip ve Analiz Uygulaması — Mimari ve Teknik Spesifikasyonlar

Bu doküman, uygulamanın veritabanı şeması, maliyet hesaplama yöntemleri, dış servis entegrasyonları, kullanıcı arayüzü tasarımı ve diğer teknik gereksinimlerini içeren referans rehberidir.

---

## 1. Veritabanı Şeması (SQLite)

Tablolar SQLAlchemy ORM ile modellenmiştir.

### `assets` tablosu — Varlık tanımları
- `id` (PK, Integer)
- `code` (Unique, String; örn: `THYAO` veya `AFT`)
- `name` (String)
- `asset_type` (Enum: `BIST`, `TEFAS`)
- `currency` (String, varsayılan `TRY`)
- `created_at` (DateTime)
- `updated_at` (DateTime)

### `transactions` tablosu — İşlem geçmişi
- `id` (PK, Integer)
- `asset_id` (FK → assets.id)
- `transaction_type` (Enum: `BUY`, `SELL`, `DIVIDEND`, `SPLIT`)
- `date` (Date)
- `quantity` (Numeric)
- `unit_price` (Numeric)
- `commission` (Numeric, varsayılan 0)
- `tax` (Numeric, varsayılan 0)
- `note` (Text, opsiyonel)
- `created_at` (DateTime)

### `price_history` tablosu — Tarihsel fiyat kayıtları
- `id` (PK, Integer)
- `asset_id` (FK → assets.id)
- `date` (Date)
- `close_price` (Numeric)
- UNIQUE(`asset_id`, `date`)

### `portfolio_snapshots` tablosu — Günlük toplam portföy değerleri
- `id` (PK, Integer)
- `date` (Date, UNIQUE)
- `total_value_try` (Numeric)
- `total_value_usd` (Numeric)
- `total_cost_try` (Numeric)
- `unrealized_pnl_try` (Numeric)

### `alerts` tablosu — Fiyat uyarıları
- `id` (PK, Integer)
- `asset_id` (FK → assets.id)
- `alert_type` (Enum: `PRICE_ABOVE`, `PRICE_BELOW`, `PCT_CHANGE_ABOVE`, `PCT_CHANGE_BELOW`)
- `threshold` (Numeric)
- `is_active` (Boolean)
- `triggered_at` (DateTime, nullable)
- `created_at` (DateTime)

### `settings` tablosu — Ayarlar
- `key` (PK, String)
- `value` (Text)
- Anahtarlar: `theme` (`system`/`light`/`dark`), `default_currency` (`TRY`/`USD`), `refresh_interval_minutes`, `cost_method` (`WAC`/`FIFO`/`LIFO`), `notifications_enabled`, `language` (`tr`), `last_backup_date`

---

## 2. Ortalama Maliyet ve K/Z Hesaplama Metodolojileri

- **WAC (Weighted Average Cost / Ağırlıklı Ortalama):**
  - Alımlarda: `Toplam Maliyet = Eski Maliyet + Alım Tutarı + Komisyon + Vergi`
  - Satışlarda: `Gerçekleşen K/Z = Net Satış Geliri - (Satılan Adet * Ortalama Birim Maliyet)`
- **FIFO (First-In, First-Out) ve LIFO (Last-In, First-Out):**
  - Alım partileri envanter kuyruğunda (`deque` veya `list`) saklanır.
  - Satış yapıldığında kuyruk/yığın sırasına göre partilerden eksiltme yapılır ve gerçekleşen K/Z hesaplanır.
- **XIRR (Yıllık Para-Ağırlıklı Getiri):**
  - Nakit akışlarının tarih ve tutarlarına göre Newton-Raphson yöntemiyle getiri oranı hesaplanır.

---

## 3. Veri Kaynakları ve Entegrasyon Detayları

- **TEFAS Servisi:**
  - `tefas-crawler` kütüphanesini kullanır. İstek aralıkları 500ms limitlidir ve 3 kez exponential backoff geri çekilme mantığı uygulanır.
- **BIST Servisi:**
  - Birincil kaynak `yfinance` `.IS` sonekiyle çalışır.
  - İkincil kaynak (Fallback) `IsYatirimService` üzerinden İş Yatırım JSON API endpoint'lerini (`HGDG_KAPANIS`/`HGDG_TARIH`) sorgular.
- **Döviz Servisi:**
  - TCMB XML endpoint (`https://www.tcmb.gov.tr/kurlar/today.xml`) kullanılarak USD/TRY kuru 24 saat önbelleğe alınır.

---

## 4. UI / UX Tasarım Sistemi ve Ekranlar

### Renk Paleti
- **Aksan / Vurgu:** `#E30A17` (Türk Kırmızısı - yalnızca UI aksanlarında kullanılır; aktif sekme, buton vurgusu vb.)
- **İkincil Vurgu:** `#00B5E2` (Turkuaz)
- **Kâr (Pozitif):** `#10B981` (Zümrüt Yeşili)
- **Zarar (Negatif):** `#B91C1C` / `#DC2626` (Asla ana vurgu rengiyle karıştırılmaz)

### Ekranlar ve Metrikler
1. **Dashboard:** KPI kartları (Toplam Değer, Günlük Değişim, Toplam K/Z, En İyi/Kötü Pozisyon), varlık donut grafiği, 90 günlük portföy değeri çizgi grafiği ve son 5 işlem.
2. **Portföy Tablosu:** Detaylı varlık listesi, sıralama, düzenleme/silme ve anlık fiyat tazeleme butonları.
3. **İşlem Geçmişi:** Kronolojik alım/satım/temettü/bölünme kayıtları ve filtreler.
4. **Analiz Sayfası:** Performans metrikleri (Sharpe, Volatilite, Max Drawdown), varlık dağılım pastası ve benchmark karşılaştırma grafikleri (BIST 100, Altın, Enflasyon vs.).
5. **Uyarılar ve Ayarlar:** Fiyat alarmları, native OS bildirimleri (`plyer`), tema seçimi (`system`/`light`/`dark`), maliyet metodu seçimi ve veri yedekleme yönetimi.

---

## 5. Uygulama Altyapı İşlevleri

- **Arka Plan Zamanlayıcı:** Fiyat güncellemeleri `QThread` içinde çalıştırılarak arayüzün kilitlenmesi engellenir.
- **Otomatik Yedekleme:** Uygulama açılışında son yedekten 7 gün geçtiyse otomatik olarak `data/backups/backup_YYYYMMDD_HHMMSS.db` konumuna yedek alınır. Son 10 yedek saklanır, eskiler silinir.
- **Loglama:** `logs/app.log` (genel) ve `logs/prices.log` (fiyat çekim) olarak 5MB limitli 5 rotasyonlu `RotatingFileHandler` ile yapılandırılmıştır.
