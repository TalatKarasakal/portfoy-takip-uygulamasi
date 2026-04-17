# Kişisel Yatırım Portföyü Takip ve Analiz Uygulaması

Bu uygulama BIST hisse senetleri ve TEFAS yatırım fonlarını tek elden yönetmek, ortalama maliyet (WAC, FIFO, LIFO) hesaplamaları yapmak ve finansal performans (XIRR) analizi sunmak için PySide6 ve SQLAlchemy kullanılarak geliştirilmiştir.

## Özellikler
- **BIST ve TEFAS Desteği**: Gerçek zamanlı ve tarihsel veri entegrasyonu (yfinance, tefas-crawler).
- **Esnek Maliyet Yönetimi**: Opsiyonel WAC, FIFO veya LIFO temelli kâr hesaplamaları.
- **Portföy Analizi**: Detaylı Metrikler (Sharpe, XIRR), varlık sınıfı pie grafiği ve karşılaştırma çizgi grafikleri.
- **Yerel ve Güvenli Veri**: Sunucu bileşeni yoktur, tüm veri makinenizde saklanır ve otomatik rotasyonlu yedekleme yapılır (SQLite).
- **Tema**: Açık veya koyu tema modu.
- **Excel/CSV Aktarımı**: Portföy transferi veya işlemlerin içeri/dışarı aktarımı.

## Kurulum ve Geliştirme

**1. Repo'yu İndirin:**
```bash
git clone <repo-url>
cd portfolio_tracker
```

**2. Sanal Ortam Oluşturun ve Bağımlılıkları Yükleyin:**
```bash
python3 -m venv venv
source venv/bin/activate  # macOS / Linux
# veya: venv\Scripts\activate.bat  # Windows

pip install -r requirements.txt
```

**3. Çalıştırın:**
```bash
python main.py
```

## Dağıtım (Paketleme)

Uygulama kodunu çalıştırılabilir (.exe veya .dmg) dosyaya bağlamak için:
```bash
pyinstaller portfolio_tracker.spec
```

*Not: macOS makinesi üzerinden DMG oluşturmak için ekstra olarak `create-dmg` kullanılabilir.*
