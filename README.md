# Portföy Takip Uygulaması

BIST hisselerini ve TEFAS fonlarını birden fazla portföyde izleyen, nakit hareketlerini ve işlem geçmişini yerel SQLite veritabanında tutan PySide6 masaüstü uygulamasıdır. Sunucu bileşeni yoktur; kullanıcı verileri varsayılan olarak cihazdan çıkmaz.

[Türkçe](#türkçe) · [English](#english)

---

## Türkçe

### Özellikler

- Ana portföy, ayrı portföyler ve salt-okunur konsolide görünüm
- Alım, satım, temettü, split, masraf, para yatırma ve çekme kayıtları
- WAC, FIFO ve LIFO maliyetleri; açık lotlar ve satış eşleşmeleri
- Gerçekleşmiş/gerçekleşmemiş kâr-zarar, TWR ve XIRR analizi
- BIST, TEFAS, döviz ve benchmark fiyatları için kaynak/tazelik bilgisi
- Temettü planı, izleme listesi ve fiyat uyarıları
- Önizlemeli ve geri alınabilir Excel içe aktarma
- Özet veya tam denetim PDF raporu
- Doğrulanmış atomik yedekleme, geri yükleme önizlemesi ve bakım araçları
- Açık/koyu tema, klavye kısayolları ve erişilebilir kontrol açıklamaları

### Gereksinimler ve kurulum

Python 3.12 önerilir; desteklenen en düşük sürüm Python 3.11'dir.

```bash
cd portfolio_tracker
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell aktivasyonu:

```powershell
cd portfolio_tracker
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`pyproject.toml` çalışma ve geliştirme bağımlılıklarının tek kaynağıdır.

### Çalıştırma

```bash
cd portfolio_tracker
portfolio-tracker
```

Kaynak giriş noktası doğrudan da çalıştırılabilir:

```bash
python main.py
```

İlk şema yükseltmesinde uygulama değişiklikleri önizletir ve kullanıcı onayı ister. Onaydan sonra migration başlamadan doğrulanmış bir güvenlik yedeği oluşturulur. Gerçek veritabanı `portfolio_tracker/data/portfolio.db`, yedekler `portfolio_tracker/data/backups/` altında tutulur. Paketlenmiş uygulama kullanıcı verilerini ev dizinindeki `.portfolio_tracker/` klasörüne yazar.

### Veri kaynakları

- `yfinance`: BIST hisseleri
- `tefas-crawler`: TEFAS fonları
- TCMB: döviz kurları

Manuel yenileme önbelleği atlar. Otomatik yenileme piyasa saatleri, asgari istek aralığı ve servis önbellekleriyle sınırlandırılır. Üçüncü taraf sağlayıcıların erişilebilirliği, fiyatlandırması ve kota koşulları ilgili sağlayıcının güncel kurallarına bağlıdır.

### İsteğe bağlı asistan

Yerel Ollama veya Google Gemini sağlayıcısı kullanılabilir. Yerel analizler sağlayıcı seçilmeden çalışır. Gemini anahtarı işletim sisteminin güvenli anahtar kasasında saklanır; kasa kullanılamıyorsa bulut sağlayıcısı etkinleşmez. Buluta gönderilecek alanlar ilk kullanımda açıkça gösterilir ve sürümlü onay alınır. Görüntüden ve doğal dilden işlem çıkarma özellikleri deneysel olup kayıt öncesinde kullanıcı doğrulaması ister.

### Geliştirme kontrolleri

```bash
cd portfolio_tracker
ruff check app tests main.py mac_identity.py smoke_test.py
mypy app main.py mac_identity.py
QT_QPA_PLATFORM=offscreen pytest -W error
QT_QPA_PLATFORM=offscreen python smoke_test.py
python -m build --wheel
portfolio-tracker --smoke-test
```

Testler geçici SQLite veritabanları kullanır. Geliştirme ve paketleme doğrulaması gerçek `data/portfolio.db` dosyasını değiştirmemelidir.

### Paketleme

```bash
cd portfolio_tracker
pyinstaller --noconfirm portfolio_tracker.spec
```

PyInstaller tanımı migration dosyalarını, QSS temalarını, fontları ve uygulama ikonunu pakete ekler. CI; Ruff, MyPy, uyarıları hata sayan testler, başsız GUI smoke testi, wheel giriş noktası ve macOS/Windows/Linux PyInstaller smoke kontrollerini çalıştırır.

#### Kurulum dosyaları

Apple Silicon macOS DMG dosyası:

```bash
cd portfolio_tracker
pyinstaller --noconfirm --clean portfolio_tracker.spec
bash packaging/macos/build_dmg.sh dist release 1.0.0
```

Windows x64 Setup.exe dosyası Windows üzerinde Inno Setup 6 ile üretilir:

```powershell
cd portfolio_tracker
pyinstaller --noconfirm --clean portfolio_tracker.spec
.\packaging\windows\build_installer.ps1 -SourceDir dist\PortfolioTracker -OutputDir release -Version 1.0.0
```

CI, macOS ve Windows kurulum dosyalarını SHA-256 dosyalarıyla birlikte ayrı artefaktlar olarak yükler. Yerel çıktılar `portfolio_tracker/release/` altında oluşur. Sertifika sağlanmadığında paketler kişisel kurulum için imzasızdır; genel dağıtımda Apple Developer ID/notarization ve Windows Authenticode imzası kullanılmalıdır.

### Mimari

Uygulama MVVM katmanlarına ayrılmıştır: View yalnızca ViewModel sinyalleri ve render verileriyle çalışır; SQLAlchemy modelleri ile servisler ViewModel katmanının arkasındadır. Uzun işlemler Session veya ORM nesnesi taşımayan worker'larda yürütülür. Ayrıntılı şema ve tasarım kararları [mimari dokümanında](docs/architecture_and_spec.md) bulunur.

PySide6 LGPL lisansı altında dağıtılır. Paketleme sırasında lisans bildirimleri ile LGPL yeniden bağlantı koşulları gözetilmelidir.

---

## English

A PySide6 desktop application for tracking BIST equities and TEFAS funds across
multiple portfolios. Cash movements and transaction history are stored in a
local SQLite database. There is no server component, and user data stays on the
device by default.

### Features

- Multiple portfolios and a read-only consolidated view
- Buy, sell, dividend, split, fee, deposit and withdrawal records
- WAC, FIFO and LIFO cost bases, open lots and sale matches
- Realised/unrealised profit and loss, TWR and XIRR analytics
- Source and freshness metadata for BIST, TEFAS, FX and benchmark prices
- Dividend plans, watchlists and price alerts
- Previewed, reversible Excel imports
- Summary and full-audit PDF reports
- Verified atomic backup, restore preview and database maintenance tools
- Light/dark themes, keyboard shortcuts and accessible controls

### Requirements and setup

Python 3.12 is recommended; Python 3.11 is the minimum supported version.

```bash
cd portfolio_tracker
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

Windows PowerShell:

```powershell
cd portfolio_tracker
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
```

`pyproject.toml` is the single source for runtime and development dependencies.

### Running

```bash
cd portfolio_tracker
portfolio-tracker
```

The source entry point can also be run directly with `python main.py`.

On the first schema upgrade, the application previews the changes and requests
confirmation. After approval, it creates a verified safety backup before the
migration starts. Packaged applications store user data under
`~/.portfolio_tracker/`.

### Data sources

- `yfinance`: BIST equities
- `tefas-crawler`: TEFAS funds
- TCMB: foreign-exchange rates

Manual refresh bypasses caches. Automatic refresh is constrained by market
hours, request intervals and per-service TTL values. Availability, pricing and
quota conditions depend on each provider's current terms.

### Optional assistant

Local Ollama and Google Gemini providers are supported. Local analytics work
without selecting a provider. Gemini keys are stored in the operating system's
secure credential vault; the cloud provider remains disabled when a secure
vault is unavailable. The fields sent to the cloud are shown before first use
and require versioned consent. Image and natural-language transaction extraction
are experimental and always require user confirmation before saving.

### Development checks

```bash
cd portfolio_tracker
ruff check app tests main.py mac_identity.py smoke_test.py
mypy app main.py mac_identity.py
QT_QPA_PLATFORM=offscreen pytest -W error
QT_QPA_PLATFORM=offscreen python smoke_test.py
python -m build --wheel
portfolio-tracker --smoke-test
```

Tests use temporary SQLite databases and must not modify
`data/portfolio.db`.

### Packaging

```bash
cd portfolio_tracker
pyinstaller --noconfirm portfolio_tracker.spec
```

Apple Silicon macOS DMG:

```bash
cd portfolio_tracker
pyinstaller --noconfirm --clean portfolio_tracker.spec
bash packaging/macos/build_dmg.sh dist release 1.0.0
```

Windows x64 Setup.exe, built on Windows with Inno Setup 6:

```powershell
cd portfolio_tracker
pyinstaller --noconfirm --clean portfolio_tracker.spec
.\packaging\windows\build_installer.ps1 -SourceDir dist\PortfolioTracker -OutputDir release -Version 1.0.0
```

CI uploads macOS and Windows installers as separate artifacts together with
their SHA-256 files. Without platform signing certificates, these packages are
intended for personal installation. Public distribution should use Apple
Developer ID/notarization and Windows Authenticode signing.

### Architecture

The application follows MVVM: views consume only ViewModel signals and render
data; SQLAlchemy models and services remain behind the ViewModel layer.
Long-running workers do not carry Sessions or ORM entities. Detailed schema and
design decisions are documented in
[architecture_and_spec.md](docs/architecture_and_spec.md).

PySide6 is distributed under the LGPL. Distribution must observe its notice and
relinking requirements.
