# Portföy Takip Uygulaması

Kişisel BIST hisse senetleri ve TEFAS yatırım fonları portföylerini izlemek, analiz etmek ve işlem geçmişiyle birlikte değerlendirmek için geliştirilen yerel masaüstü uygulamasıdır. Uygulama sunucu bileşeni olmadan çalışır; portföy verileri kullanıcının makinesindeki SQLite veritabanında tutulur.

## Öne Çıkan Analitik Özellikler

- XIRR, Sharpe oranı, maksimum düşüş (Max Drawdown) ve volatilite gibi performans metrikleri.
- WAC, FIFO ve LIFO maliyet bazı yöntemleriyle gerçekleşmiş ve gerçekleşmemiş kar/zarar takibi.
- PyQtGraph tabanlı tarihsel fiyat, portföy değeri ve karşılaştırmalı performans grafikleri.
- BIST hisse senetleri ve TEFAS fonları için güncel fiyat ve geçmiş veri takibi.
- Yerel işlem geçmişi üzerinden portföy dağılımı, maliyet, getiri ve risk analizi.

## Teknoloji Yığını

- Python 3.11+
- PySide6 (Qt6)
- SQLAlchemy 2.x
- SQLite
- PyQtGraph
- httpx

PySide6, LGPL lisansı altında dağıtılır. Uygulamanın dağıtımında bu lisansın yeniden bağlantı ve bildirim koşulları dikkate alınmalıdır.

## Veri Kaynakları

- `tefas-crawler`: TEFAS yatırım fonu verileri
- `yfinance`: BIST hisse senedi verileri (`.IS` uzantılı semboller)
- TCMB XML: Günlük USD/TRY kuru

## Mimari

Uygulama MVVM mimarisiyle yapılandırılmıştır. View katmanı PySide6 arayüz bileşenlerinden, ViewModel katmanı UI durumu ve bağlama mantığından, Model katmanı ise SQLAlchemy ORM varlıklarından sorumludur.

## Kurulum

```bash
cd portfolio_tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell için sanal ortam aktivasyonu:

```powershell
cd portfolio_tracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Çalıştırma

Uygulamanın kaynak koddaki giriş noktası `portfolio_tracker/main.py` dosyasıdır.

```bash
cd portfolio_tracker
python main.py
```

## Paketleme

Dağıtım hedefleri macOS için `.dmg`, Windows için `.exe` artefaktlarıdır. Derleme ve paketleme çıktıları ile bunlara ait geçici yapılandırma dosyaları repoda tutulmaz.

## Yapay Zeka Özellikleri

Uygulamada yerel veya bulut sağlayıcısıyla çalışan isteğe bağlı bir asistan
bulunur. Asistan sol menüdeki **"Asistan"** sekmesinden kullanılır.

### Sağlayıcı seçenekleri

Ayarlar > **Yapay Zeka** bölümünden seçilir:

- **Ollama** — Kendi makinenizde çalışan yerel modeller (llama3.1, qwen2.5,
  gemma2 vb.). İnternet gerektirmez, tamamen ücretsiz ve gizlidir.
  Kurulum: https://ollama.com (`ollama pull llama3.1`).
- **Google Gemini** — Fiyatı, ücretsiz kotası ve kullanım sınırları Google'ın
  güncel koşullarına bağlı olan bulut modeli. API anahtarı işletim sisteminin
  güvenli kasasında tutulur; portföy verisi yalnız sürümlü kullanıcı onayından
  sonra gönderilir: https://aistudio.google.com/app/apikey

### Özellikler

1. **Portföy Asistanı (sohbet)** — Portföyünüz hakkında doğal dilde soru sorun.
2. **Otomatik Portföy Özeti** — Güncel durumun kısa Türkçe özeti.
3. **Doğal Dil ile İşlem Girişi (Deneysel)** — Sonuç doğrulanmadan kaydedilmez.
4. **Akıllı Risk Analizi** — Konsantrasyon ve çeşitlendirme uyarıları (LLM'siz, anında).
5. **Teknik Analiz** — SMA, EMA, RSI, MACD ve trend sinyali (yerel hesaplama).
6. **Anomali Tespiti** — Olağandışı fiyat hareketlerini yakalar (yerel hesaplama).
7. **Haber Duygu Analizi** — Bir varlık hakkındaki güncel haberlerin duygu skoru.
8. **Hedef Bazlı Öneri** — Risk + teknik göstergelere dayalı iyileştirme önerileri.
9. **Görüntüden Aktarım (Deneysel)** — Bulut sağlayıcısında ayrıca dosya gönderim
   onayı ister ve bulunan kayıtları kaydetmeden önce gösterir.

> Teknik analiz, anomali tespiti ve risk analizi tamamen yerel ve LLM'siz
> çalışır; sağlayıcı seçilmemiş olsa bile kullanılabilir.
