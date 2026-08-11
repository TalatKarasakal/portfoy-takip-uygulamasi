# 📌 Portföy Takip ve Analiz Uygulaması — Proje Takip Belgesi

Bu belge aktif işleri, kullanıcı kontrolü bekleyen çözümleri ve reddedilen önerileri takip eder.

- **Son güncelleme:** 2026-08-11
- **Aktif madde sayısı:** 0
- **Kontrol bekleyen çözüm sayısı:** 40
- **Son otomatik doğrulama:** 142 test, Ruff, MyPy, GUI smoke, wheel smoke ve macOS PyInstaller smoke

---

## 🧭 0. Takip Standardı

- `TODO-*`: Küçük işler ve notlar
- `PT-*`: Doğrulanmış sorunlar
- `FTR-*`: Yeni özellikler
- `SIM-*`: Sadeleştirme ve kaldırma işleri
- Kimlikler yeniden numaralandırılmaz veya başka işler için tekrar kullanılmaz.
- Kodlanan çözüm, kullanıcı doğrulamasına kadar **Kontrol Bekliyor** durumunda kalır.
- Kullanıcı onayından sonra kayıt `PROJECT_HISTORY.md` dosyasına taşınır.
- Reddedilen öneriler gerekçesiyle birlikte belgede tutulur ve tekrar önerilmez.

### Önerilen manuel doğrulama sırası

1. PT-007 ve PT-014: yedekleme, geri yükleme ve ilk migration güvenliği
2. PT-006, PT-005 ve FTR-007: işlem, içe aktarma ve nakit doğruluğu
3. PT-008 ve FTR-011: anahtar kasası ve bulut onayı
4. Kalan analiz, fiyat, UI ve paketleme kontrolleri

---

## 📋 1. Yapılacaklar

*(Aktif yapılacak bulunmamaktadır.)*

---

## ⚠️ 2. Tespit Edilen Sorunlar ve Çözüm Önerileri

*(Aktif sorun bulunmamaktadır.)*

---

## 🧪 3. Kontrol Edilecek Çözümler

> Aşağıdaki değişiklikler kodlandı ve otomatik testlerden geçti. Kullanıcı manuel doğrulamayı tamamlayana kadar geçmiş dosyasına taşınmayacaktır.

| Kimlik | Çözüm | Commit | Otomatik doğrulama | Kullanıcı kontrolü |
|---|---|---|---|---|
| PT-007 | **Kontrol Bekliyor.** [GPT-5] SQLite Backup API, `quick_check`, şema doğrulaması, güvenlik yedeği ve atomik restore eklendi; yedek başarısızsa veri silme başlamıyor. | `43b1d88` + `a2a970e` | `test_backup_service.py`: aktif yazma, bozuk şema, atomik restore ve güvenlik yedeği hatası; `test_security.py`: silme engeli. | Ayarlar > Veritabanı Bakımı'ndan yedek oluşturun, önizleyin ve geçici bir yedeği geri yükleyin; bozuk dosyanın reddedildiğini doğrulayın. |
| PT-001 | **Kontrol Bekliyor.** [GPT-5] UTC zamanları ortak `UTCDateTime` türü ve timezone-aware üretimle standartlaştırıldı. | `134fbb1` | Migration testleri ve `pytest -W error`; Python 3.12 altında datetime uyarısı yok. | Yeni bir işlem oluşturup yeniden açın; oluşturulma zamanının kaybolmadığını doğrulayın. |
| PT-003 | **Kontrol Bekliyor.** [GPT-5] Test fixture'ları Session kapatma ve Engine dispose garantisiyle düzenlendi. | `134fbb1` | 142 test `-W error` ile geçti; geçici SQLite kaynak uyarısı yok. | Manuel işlem gerekmez; CI test adımının temiz tamamlandığını kontrol edin. |
| PT-014 | **Kontrol Bekliyor.** [GPT-5] Sürümlü Alembic zinciri, merkezi SQLite pragma'ları, migration öncesi yedek ve doğrulanmış geçici kopya üzerinde atomik yükseltme eklendi. | `134fbb1` + `a2a970e` | `test_migrations.py`: yeni/eski/bilinmeyen şema, veri taşıma ve zorlanmış migration hatasında aktif DB'nin korunması. | Gerçek DB'nin ayrı kopyısıyla uygulamayı açın; önizleme/onay, güvenlik yedeği ve başarılı açılışı doğrulayın. |
| SIM-001 | **Kontrol Bekliyor.** [GPT-5] Elle tutulan `initial.sql` ve `dump_schema.py` kaldırıldı; tek şema kaynağı Alembic oldu. | `134fbb1` | Migration zinciri sıfırdan güncel şemayı kuruyor ve 0005 head sürümüne ulaşıyor. | Projede eski şema betiklerinin bulunmadığını, `alembic upgrade head` akışının çalıştığını kontrol edin. |
| FTR-002 | **Kontrol Bekliyor.** [GPT-5] Çoklu portföy, salt-okunur “Tüm Portföyler” ve portföy bazlı izleme listesi eklendi. | `0f8214f` | `test_portfolio_account_service.py`: benzersiz portföy, varsayılan koruması ve konsolide izleme listesi. | İki portföy oluşturun; aynı varlığı ayrı izleme listelerine ekleyip konsolide görünümü kontrol edin. |
| FTR-007 | **Kontrol Bekliyor.** [GPT-5] Nakit defteri; yatırma, çekme, düzeltme ve işlem nakit etkilerini tek zaman çizelgesinde birleştiriyor. | `0f8214f` + `b0e342c` | `test_cash_balance_combines_external_and_transaction_flows` ve `test_twr_is_neutral_to_external_deposit`. | Para yatırın, alım ve satış yapın; toplam değerin nakit + menkul kıymet olduğunu doğrulayın. |
| TODO-002 | **Kontrol Bekliyor.** [GPT-5] Miktar ve fiyatlar `Decimal` ile 6 basamak; toplam para değerleri 2 basamak politikasına geçirildi. | `0f8214f` + `8013fd1` | `test_create_uses_six_decimal_precision` ve formatlama testleri. | `0,123456` adet/fiyatlı işlem girin; kayıt ve gösterimde hassasiyetin korunduğunu kontrol edin. |
| TODO-003 | **Kontrol Bekliyor.** [GPT-5] Portföy-varlık-tarih-ID transaction indeksi eklendi; gereksiz price_history indeksi sorgu planıyla elendi. | `0f8214f` | `test_legacy_migration_infers_opening_cash_and_adds_query_index` içindeki `EXPLAIN QUERY PLAN` doğrulaması. | Uzun işlem geçmişinde varlık filtresi ve tarih sıralamasının akıcı kaldığını kontrol edin. |
| PT-006 | **Kontrol Bekliyor.** [GPT-5] Bütün giriş kanalları kodlanmış hatalar üreten ortak `TransactionService` doğrulamasına bağlandı. | `8013fd1` | `test_transaction_service.py`: sıfır/negatif değer, gelecek tarih, split, masraf, fazla satış ve geçmiş bakiye testleri. | Pozisyondan fazla satış ve negatif masraf girmeyi deneyin; kayıt oluşmadan anlaşılır hata görünmelidir. |
| PT-011 | **Kontrol Bekliyor.** [GPT-5] Aynı günlü işlemler `(date, id)` sırasıyla deterministik hale getirildi. | `8013fd1` | `test_same_day_order_is_deterministic_and_split_affects_later_sale`. | Aynı gün alım, split ve satış ekleyin; yeniden açınca adet ve maliyetin değişmediğini doğrulayın. |
| PT-005 | **Kontrol Bekliyor.** [GPT-5] Excel tarih/sayı/başlık normalizasyonu ve bütün dosyayı kapsayan tek transaction eklendi. | `ce5c6cd` | `test_real_excel_round_trip_preserves_all_entities` ve `test_one_bad_row_blocks_entire_file`. | Dışa aktarın, yeni geçici DB'ye içe alın; portföy, işlem, nakit ve plan sayılarını karşılaştırın. |
| FTR-006 | **Kontrol Bekliyor.** [GPT-5] Satır durumlu önizleme, varsayılan atlanan mükerrerler, tam rollback ve güvenli son-batch geri alma eklendi. | `ce5c6cd` + `a2a970e` | Import mükerrer/undo/rollback testleri ve `test_import_preview_disables_error_rows_and_apply_action`. | Hatalı ve mükerrer satırlı dosyayı açın; hatalı satır seçilememeli, mükerrer varsayılan kapalı olmalı. |
| PT-008 | **Kontrol Bekliyor.** [GPT-5] Gemini anahtarı sistem kasasına taşındı, header kullanımı ve merkezi log maskeleme eklendi; düz metin migration ile siliniyor. | `0a84921` | `test_security.py`, `test_gemini_uses_api_key_header_not_url` ve `test_plaintext_gemini_key_is_removed_by_migration`. | Gemini anahtarını kaydedin; DB/yedek içinde anahtar metni bulunmadığını ve yeniden açınca yapılandırılmış göründüğünü kontrol edin. |
| FTR-011 | **Kontrol Bekliyor.** [GPT-5] Sürümlü bulut veri onayı, gönderilecek alan listesi ve görüntü yükleme bildirimi eklendi. | `0a84921` + `a2a970e` | `test_cloud_provider_is_blocked_without_versioned_consent`; onaysız sağlayıcı çağrısı engelleniyor. | Gemini'yi ilk kez seçin; alan listesini görün, reddedince çağrı yapılmadığını doğrulayın. |
| SIM-004 | **Kontrol Bekliyor.** [GPT-5] Sağlayıcı metinleri sabit ücretsiz iddiaları yerine güncel lisans, fiyat ve kota koşullarına bağlandı. | `0a84921` + `a2a970e` | README/UI metin denetimi, Ruff ve GUI smoke. | Ayarlar > Yapay Zeka bilgilendirmesinde sağlayıcı koşulları uyarısını kontrol edin. |
| SIM-005 | **Kontrol Bekliyor.** [GPT-5] Doğal dil işlem ve görüntü aktarımı “Deneysel” olarak etiketlendi; kayıt öncesi doğrulama zorunlu kaldı. | `0a84921` | AI yardımcı testleri ve GUI smoke doğrulama diyaloglarını oluşturuyor. | Asistan sekmesinde iki deneysel etiketi ve kaydetmeden önce sonuç doğrulama ekranını kontrol edin. |
| PT-002 | **Kontrol Bekliyor.** [GPT-5] Worker girdileri immutable DTO'lara çevrildi; ORM nesnesi ve Session thread'ler arasında taşınmıyor. | `6e2fccd` | `test_mvvm_architecture.py` ve paralel fiyat/yenileme testleri. | Çok varlıklı yenileme başlatın; arayüzün kararlı kaldığını doğrulayın. |
| PT-004 | **Kontrol Bekliyor.** [GPT-5] Benchmark sonucu ViewModel üzerinden tipli durum nesnesiyle aktarılıyor; veri yokluğu ve bağlantı hatası ayrılıyor. | `6e2fccd` + `962bd54` | Fiyat fallback/çevrimdışı testleri ve GUI smoke benchmark render'ı. | İnterneti kapatıp Analiz ekranını açın; grafik çökmemeli ve çevrimdışı açıklaması görünmeli. |
| PT-016 | **Kontrol Bekliyor.** [GPT-5] Bağlantı testi, import, PDF, bakım ve yenileme ilerleme/iptal sinyalli worker'lara taşındı; kapanışta `shutdown()` uygulanıyor. | `6e2fccd` + `a2a970e` | `test_views_do_not_own_threads`, `test_worker_shutdown_waits_for_running_task` ve GUI smoke kapanışı. | Yenileme veya bağlantı testi sürerken pencereyi kapatın; thread uyarısı ya da çökme olmamalı. |
| PT-017 | **Kontrol Bekliyor.** [GPT-5] View katmanındaki servis/model/veritabanı importları kaldırıldı; ViewModel sinyalleri kullanılıyor. | `6e2fccd` | `test_views_do_not_import_models_database_or_services`. | Uygulamanın tüm sekmelerini dolaşın; veri yükleme ve işlemlerin aynı şekilde çalıştığını doğrulayın. |
| TODO-001 | **Kontrol Bekliyor.** [GPT-5] BIST ve TEFAS için piyasa saatli, tatil/yarım gün ayarlı otomatik yenileme politikası eklendi; manuel yenileme bağımsız. | `962bd54` | `test_refresh_policy_market_hours_holidays_and_manual_override` ve yarım gün testi. | Saat/tatil ayarını değiştirin; otomatik yenilemeyi ve saat dışındaki manuel yenilemeyi kontrol edin. |
| PT-012 | **Kontrol Bekliyor.** [GPT-5] Manuel yenileme daima `force_refresh=True`; çalışan yükleme sırasında gelen zorunlu istek korunuyor. | `962bd54` | `test_forced_refresh_is_preserved_while_loader_is_running` ve BIST/TEFAS force-refresh testleri. | Arka arkaya iki kez “Şimdi Yenile”ye basın; ikinci zorunlu yenilemenin ilkinden sonra çalıştığını kontrol edin. |
| PT-013 | **Kontrol Bekliyor.** [GPT-5] TEFAS erişimi süreç genelinde kilitlendi ve başlangıçlar arasında en az 500 ms sınırı getirildi. | `962bd54` | `test_tefas_crawler_calls_are_process_serialized`. | Birden fazla TEFAS fonunu yenileyin; eşzamanlı çağrı hatası oluşmadığını kontrol edin. |
| PT-018 | **Kontrol Bekliyor.** [GPT-5] Fiyat 15 dk, kur 24 saat, benchmark 6 saat ve fon adı 7 gün TTL politikasına geçirildi. | `962bd54` | `test_cache_honors_per_entry_ttl_with_fake_clock` ve servis önbellek testleri. | Manuel yenilemenin cache'i atladığını, normal açılışın mevcut cache'i kullandığını kontrol edin. |
| FTR-008 | **Kontrol Bekliyor.** [GPT-5] Fiyat DTO'suna kaynak, fiyat tarihi, çekilme zamanı ve canlı/cache/eski/çevrimdışı durumu eklendi. | `962bd54` | BIST, TEFAS ve fallback testleri tipli sonuç durumlarını doğruluyor. | Portföy fiyat hücresinin ipucunda kaynak, fiyat tarihi ve tazelik durumunu kontrol edin. |
| PT-009 | **Kontrol Bekliyor.** [GPT-5] Toplam değer, açık pozisyon getirisi, gerçekleşmiş/gerçekleşmemiş K/Z ve TWR ayrıldı; pay/payda bilgileri eklendi. | `b0e342c` | TWR yatırma nötrlüğü, eski snapshot güvenilirliği ve konsolide geçmiş testleri. | Fiyatı değiştirmeden para yatırın; TWR kartının değişmediğini kontrol edin. |
| PT-010 | **Kontrol Bekliyor.** [GPT-5] XIRR işaret kontrollü aralıklı kök aramaya ve başarılı/hesaplanamadı/belirsiz tipli sonucuna geçirildi. | `b0e342c` + `a2a970e` | Bilinen %10, tek işaret, çoklu kök ve aşırı kök testleri. | Yetersiz nakit akışlı portföyde anlamsız dev sayı yerine “hesaplanamadı” göründüğünü kontrol edin. |
| FTR-001 | **Kontrol Bekliyor.** [GPT-5] Geçmiş temettüler ve manuel planlar aynı ekranda; “ödendi” işlemi bağlı temettüyü atomik oluşturuyor. | `b0e342c` | `test_dividend_service.py`: bağlı işlem ve eldeki adedi aşma reddi. | Bir plan ekleyip ödendi yapın; adet ön dolumunu ve bağlı DIVIDEND işlemini kontrol edin. |
| FTR-009 | **Kontrol Bekliyor.** [GPT-5] FIFO/LIFO açık lotları, WAC havuzu ve satış-lot eşleşmeleri analiz ekranına eklendi. | `b0e342c` | `test_fifo_returns_open_lots_and_sale_matches` ile WAC/FIFO/LIFO testleri. | Kademeli iki alım ve bir satış yapın; lot ekranındaki eşleşmeleri maliyet yöntemleri arasında karşılaştırın. |
| FTR-003 | **Kontrol Bekliyor.** [GPT-5] Tipli tema paleti QSS, PyQtGraph ve QtCharts bileşenlerine ortak sinyalle uygulanıyor. | `c6e3664` | GUI smoke açık/koyu/sistem temalarını ve chart render yollarını çalıştırıyor. | Tema değiştirin; grafik, pasta, tablo ve odak renklerinin birlikte değiştiğini kontrol edin. |
| FTR-004 | **Kontrol Bekliyor.** [GPT-5] Grafik hover/crosshair etkileşimi ve özet/tam denetim PDF seçenekleri eklendi. | `c6e3664` | `test_pdf_summary_and_audit_modes_create_files` ve GUI smoke grafik etkileşimleri. | Grafikte hover bilgisini deneyin; iki PDF türünü üretip tam rapordaki işlem/nakit/lot bölümlerini açın. |
| FTR-005 | **Kontrol Bekliyor.** [GPT-5] Ayarlar tipli `AppSettings` yapısına taşındı; kullanılmayan `get_setting` ve yinelenen form sözlüğü kaldırıldı. | `c6e3664` | `test_accessibility_assigns_names_and_typed_settings_validate` ve MyPy. | Geçersiz ayar değerlerini değiştirip kaydedin; güvenli varsayılana döndüğünü kontrol edin. |
| FTR-010 | **Kontrol Bekliyor.** [GPT-5] Bütünlük, yedek listesi/doğrulama, restore önizleme, taşınabilir yedek, optimize ve onaylı VACUUM bakım ekranına eklendi. | `c6e3664` | `test_database_maintenance_checks_lists_optimizes_and_vacuums`. | Ayarlar > Veritabanı Bakımı'nda bütünlük, optimize ve taşınabilir yedek işlemlerini çalıştırın. |
| FTR-012 | **Kontrol Bekliyor.** [GPT-5] Erişilebilir ad/açıklama, odak görünümü, tab sırası, kısayollar, kapanabilir sidebar ve kaydırılabilir formlar eklendi. | `c6e3664` + `a2a970e` | Erişilebilirlik, import diyalogu ve GUI smoke testleri. | Yalnız klavyeyle Ctrl+1…7, Ctrl+R ve Ctrl+B kısayollarını; dar pencere sidebar davranışını kontrol edin. |
| PT-015 | **Kontrol Bekliyor.** [GPT-5] Paket kaynakları, macOS DMG ve Windows Inno Setup kurucusuna ek olarak şeffaf master'dan türetilen beyaz/koyu tema simgeleri eklendi; çalışan uygulamanın pencere, Dock ve görev çubuğu simgesi aktif temayla değişiyor. Eski kaynak çalıştırıcısı kaldırıldı; macOS paketi tek `Portföy Takip` adı ve `com.talat.portfoytakip` kimliği altında birleştirildi. | `a2a970e` + `146c6e9` + `1c0cbb7` + `3a7315d` | 144 test, tema simgesi piksel/doğrulama testi, paket kimliği testi, GUI smoke, macOS PyInstaller smoke ve tek uygulamalı DMG bütünlük kontrolü geçti. | DMG'yi açıp yalnız bir `Portföy Takip` uygulaması bulunduğunu doğrulayın; açık, koyu ve sistem temasında pencere ile Dock simgesini kontrol edin. |
| PT-019 | **Kontrol Bekliyor.** [GPT-5] CI; kalite kontrolleri ve üç platform paket smoke sonrasında macOS DMG ile Windows Setup.exe dosyalarını SHA-256 toplamlarıyla artefakt olarak üretecek şekilde genişletildi. macOS smoke yolu tek `Portföy Takip.app` paketine yönlendirildi. | `a2a970e` + `146c6e9` + `abe8dfe` + `3a7315d` | Yerelde 144 test, Ruff, MyPy ve güncel macOS DMG doğrulaması geçti; macOS/Windows/Linux paket job'ları ve Windows kurucu üretimi başarıyla doğrulandı. | GitHub Actions'ta validate/package işlerini ve indirilebilir iki kurulum artefaktını kontrol edin. |
| PT-020 | **Kontrol Bekliyor.** [GPT-5] Homebrew Python 3.12 ve `.venv` kuruldu; `pyproject.toml` tek bağımlılık kaynağı oldu; coverage/cache/paket çıktıları ignore edildi. | `a2a970e` | Python 3.12.13, editable kurulum, Ruff, MyPy ve test paketi doğrulandı. | Yeni `.venv` ile `pip install -e ".[dev]"` ve `portfolio-tracker --smoke-test` komutlarını çalıştırın. |
| SIM-002 | **Kontrol Bekliyor.** [GPT-5] İki README kök belgede birleştirildi; `requirements.txt` kaldırıldı. | `a2a970e` | Wheel build metadata ve giriş noktası smoke doğrulaması. | Kurulum adımlarını yalnız kök README'yi kullanarak temiz ortamda uygulayın. |
| SIM-003 | **Kontrol Bekliyor.** [GPT-5] Doğrudan kullanılmayan `requests` bağımlılığı çıkarıldı; güvenli kasa için `keyring` eklendi. | `a2a970e` | Editable kurulum ve keyring güvenli/güvensiz backend testleri. | `pip install -e ".[dev]"` sonrasında Ayarlar'da sistem kasası durumunu kontrol edin. |

---

## ❌ 4. Reddedilen Öneriler

*(Henüz reddedilen öneri bulunmamaktadır.)*

---

## 🚀 5. Geliştirme ve Özellik Önerileri

*(Aktif öneri bulunmamaktadır; tüm kayıtlar kullanıcı kontrolü beklemektedir.)*
