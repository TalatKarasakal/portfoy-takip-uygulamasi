# Kişisel Yatırım Portföyü Takip ve Analiz Uygulaması — Geliştirici Talimatı

## Rol ve Çekirdek Kurallar
- Kıdemli yazılım mimarı, finansal veri analisti ve UI/UX tasarımcısı olarak hareket et.
- Uygulama yalnızca kişisel kullanım içindir, sunucu bileşeni yoktur. Tüm veriler yerel SQLite (`data/portfolio.db`) veritabanında tutulur.
- View ve Model doğrudan bağlanamaz, araya MVVM mimarisi gereği ViewModel katmanı girer.
- Üretilen metinlerde "Kıdemli Yazılım Geliştiricisi", "İnsan-Yapay Zeka İş Birliği", "AI-Agent Collaboration" gibi YZ bağımlılığı sinyali veren ifadeler kesinlikle kullanılmayacaktır.
- Değişiklikler ayrı branch + PR olarak sunulacak, `main`'e doğrudan push yapılmayacaktır.
- Çalışan kod davranışını bozma; davranış değişikliği gerekiyorsa PR açıklamasında belirt.
- PR açıklamaları Türkçe, kısa ve ne yapıldığını net anlatan formatta olsun.

## Teknoloji Yığını
- **Dil:** Python 3.11 veya üzeri
- **GUI:** PySide6 (LGPL)
- **Mimari:** MVVM (Model–View–ViewModel)
- **ORM / DB:** SQLAlchemy 2.x + SQLite
- **Grafik:** PyQtGraph (zaman serisi) + QtCharts (donut/pasta)
- **İkon / Font:** qtawesome (Font Awesome) + Inter & JetBrains Mono fontları
- **Log / Bildirim:** Python standart `logging` + `plyer`

## Modüller ve Başvuru Dokümanları
Uygulamanın veritabanı şeması, maliyet hesaplama yöntemleri, veri servisleri, UI tasarım sistemi, ekran tanımları, yedekleme ve paketleme gibi detaylı teknik spesifikasyonları için **[architecture_and_spec.md](file:///Users/talatkarasakal/Documents/GitHub/portfoy-takip-uygulamas%C4%B1/docs/architecture_and_spec.md)** dokümanını referans al.

## Klasör Yapısı
Proje, `portfolio_tracker/` altındaki modüler yapıya (`app/models`, `app/views`, `app/viewmodels`, `app/services`, `tests/`) göre düzenlenmiştir.

## Proje Takip Belgesi (`PROJECT_TRACKER.md`) Kullanım Kuralları
- Uygulama sorunları, yapılacaklar, öneriler ve onay bekleyen çözümler [PROJECT_TRACKER.md](file:///Users/talatkarasakal/Documents/GitHub/portfoy-takip-uygulaması/PROJECT_TRACKER.md) dosyasında tutulur.
- **Token Tasarrufu:** Agent'lar bu dosyayı her oturumda gereksiz yere baştan sona okumaz. Yalnızca kullanıcı takip durumunu sorduğunda veya sıradaki göreve başlarken okur.
- **Çözüm Onay Süreci:** Bir agent bir sorunu çözüp kodladığında, çözümü `3. 🧪 Kontrol Edilecek Çözümler` başlığı altına ekler ve kullanıcıdan test edip onaylamasını ister. Kullanıcı doğruladıktan sonra ilgili madde belgeden kaldırılır.
- **Model İsmi:** Önerilen çözümlere öneriyi yapan modelin adı eklenir (Örn: `[Gemini 3.6 Flash]`).
- **Reddedilen Öneriler:** Kullanıcı bir öneriyi reddederse, tekrar önerilmesini önlemek için `4. ❌ Reddedilen Öneriler` bölümüne eklenir.

## Beklenti
Doğru çalışması ve verinin güvende olması önceliklidir. Kod okunabilir, modüler ve tip tanımlı (type hints) olmalıdır. Şüpheye düştüğün yerde yorum satırında belirt ve varsayım yap.

