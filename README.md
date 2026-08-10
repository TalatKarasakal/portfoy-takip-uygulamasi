# Portföy Takip Uygulaması

BIST hisse senetleri ve TEFAS yatırım fonları için yerel masaüstü portföy takip
uygulaması.

[Türkçe](#türkçe) · [English](#english)

---

## Türkçe

Kişisel BIST hisse senetleri ve TEFAS yatırım fonları portföylerini izlemek,
analiz etmek ve işlem geçmişiyle birlikte değerlendirmek için geliştirilen
yerel masaüstü uygulamasıdır. Uygulama sunucu bileşeni olmadan çalışır;
portföy verileri kullanıcının makinesindeki SQLite veritabanında tutulur.

### Öne çıkan analitik özellikler

- XIRR, Sharpe oranı, maksimum düşüş (Max Drawdown) ve volatilite gibi
  performans metrikleri
- WAC, FIFO ve LIFO maliyet bazı yöntemleriyle gerçekleşmiş ve gerçekleşmemiş
  kar/zarar takibi
- PyQtGraph tabanlı tarihsel fiyat, portföy değeri ve karşılaştırmalı
  performans grafikleri
- BIST hisse senetleri ve TEFAS fonları için güncel fiyat ve geçmiş veri takibi
- Yerel işlem geçmişi üzerinden portföy dağılımı, maliyet, getiri ve risk analizi

### Teknoloji yığını

Python 3.11+ · PySide6 (Qt6) · SQLAlchemy 2.x · SQLite · PyQtGraph · httpx

PySide6, LGPL lisansı altında dağıtılır. Uygulamanın dağıtımında bu lisansın
yeniden bağlantı ve bildirim koşulları dikkate alınmalıdır.

### Veri kaynakları

- `tefas-crawler` — TEFAS yatırım fonu verileri
- `yfinance` — BIST hisse senedi verileri (`.IS` uzantılı semboller)
- TCMB XML — günlük USD/TRY kuru

### Mimari

Uygulama MVVM mimarisiyle yapılandırılmıştır. View katmanı PySide6 arayüz
bileşenlerinden, ViewModel katmanı UI durumu ve bağlama mantığından, Model
katmanı ise SQLAlchemy ORM varlıklarından sorumludur.

### Kurulum

```bash
cd portfolio_tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Windows PowerShell:

```powershell
cd portfolio_tracker
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

### Çalıştırma

```bash
cd portfolio_tracker
python main.py
```

### Paketleme

Dağıtım hedefleri macOS için `.dmg`, Windows için `.exe` artefaktlarıdır.
Derleme ve paketleme çıktıları ile bunlara ait geçici yapılandırma dosyaları
repoda tutulmaz.

### Yapay zekâ özellikleri

Uygulamaya, tamamen ücretsiz çalışan bir yapay zekâ asistanı eklendi.
Asistan sol menüdeki **Asistan** sekmesinden kullanılır.

**Sağlayıcı seçenekleri** (Ayarlar → Yapay Zekâ):

- **Ollama** — kendi makinenizde çalışan yerel modeller (llama3.1, qwen2.5,
  gemma2 vb.). İnternet gerektirmez, veriler cihazdan çıkmaz.
  Kurulum: https://ollama.com (`ollama pull llama3.1`)
- **Google Gemini** — ücretsiz katmanı olan bulut modeli, yalnızca bir API
  anahtarı gerekir: https://aistudio.google.com/app/apikey

**Özellikler:** portföy hakkında doğal dilde soru sorma, otomatik portföy
özeti, doğal dil ile işlem girişi ("Dün 100 THYAO aldım 280 liradan"),
konsantrasyon ve çeşitlendirme uyarıları, teknik analiz (SMA, EMA, RSI, MACD),
anomali tespiti, haber duygu analizi ve hedef bazlı öneriler.

> Teknik analiz, anomali tespiti ve risk analizi tamamen yerel ve LLM'siz
> çalışır; sağlayıcı seçilmemiş olsa bile kullanılabilir.

---

## English

A local desktop application for tracking and analysing personal portfolios of
Turkish equities (BIST) and mutual funds (TEFAS). It runs without any server
component; portfolio data is stored in a SQLite database on the user's machine.

### Analytics

- Performance metrics: XIRR, Sharpe ratio, maximum drawdown and volatility
- Realised and unrealised profit/loss with weighted-average, FIFO or LIFO cost
  basis
- Historical price, portfolio value and comparative performance charts built
  with PyQtGraph
- Current and historical data for BIST equities and TEFAS funds
- Allocation, cost, return and risk analysis from the local transaction history

### Stack

Python 3.11+ · PySide6 (Qt6) · SQLAlchemy 2.x · SQLite · PyQtGraph · httpx

PySide6 is distributed under the LGPL; its relinking and notice requirements
apply to any distribution of this application.

### Data sources

- `tefas-crawler` — TEFAS mutual fund data
- `yfinance` — BIST equity data (`.IS` suffixed symbols)
- TCMB XML — daily USD/TRY exchange rate

### Architecture

The application follows an MVVM structure: the View layer holds the PySide6
widgets, the ViewModel layer holds UI state and binding logic, and the Model
layer is made of SQLAlchemy ORM entities.

### Setup

```bash
cd portfolio_tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Packaging

Distribution targets are a `.dmg` for macOS and an `.exe` for Windows. Build
and packaging artefacts, along with their temporary configuration files, are
not tracked in the repository.

### AI assistant

The application includes an AI assistant that runs entirely on free
providers, available from the **Asistan** tab.

- **Ollama** — local models running on your own machine (llama3.1, qwen2.5,
  gemma2 and others). No internet required; data never leaves the device.
- **Google Gemini** — a cloud model with a free tier, requiring only an API key.

It supports natural-language questions about the portfolio, automatic
summaries, natural-language transaction entry, concentration and
diversification warnings, technical analysis (SMA, EMA, RSI, MACD), anomaly
detection, news sentiment analysis and goal-based suggestions.

> Technical analysis, anomaly detection and risk analysis run locally without
> an LLM and work even when no provider is configured.
