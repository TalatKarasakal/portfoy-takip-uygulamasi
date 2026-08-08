import os
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

# Test/smoke kontrolleri kullanıcı verisine dokunmadan ayrı bir veri kökü
# seçebilir. Üretimde değişken verilmez ve platform varsayılanı kullanılır.
_data_root_override = os.environ.get("PORTFOLIO_TRACKER_DATA_DIR")

# Projenin kök dizini
if getattr(sys, "frozen", False):
    # If the application is run as a bundle, the PyInstaller bootloader
    # extends the sys module by a flag frozen=True and sets the app
    # path into variable _MEIPASS'.
    ROOT_DIR = Path(sys._MEIPASS)
    # Veri dizini (Gerçek kullanıcı dosyaları, executable'ın yanında klasörde tutulsun)
    # macOS .dmg ve Windows için uygun bir yol:
    DATA_ROOT = Path.home() / ".portfolio_tracker"
else:
    ROOT_DIR = Path(__file__).resolve().parent.parent
    DATA_ROOT = ROOT_DIR

if _data_root_override:
    DATA_ROOT = Path(_data_root_override).expanduser().resolve()

DATA_DIR = DATA_ROOT / "data"
BACKUP_DIR = DATA_DIR / "backups"
LOGS_DIR = DATA_ROOT / "logs"

# Dizinleri oluştur
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(BACKUP_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# Veritabanı yolu
DATABASE_FILE = DATA_DIR / "portfolio.db"
DATABASE_URL = f"sqlite:///{DATABASE_FILE}"

# Tema Renkleri
@dataclass(frozen=True)
class ThemePalette:
    primary: str
    secondary: str
    background: str
    surface: str
    border: str
    text_primary: str
    text_secondary: str
    profit: str
    loss: str
    neutral: str


PALETTES = {
    "light": ThemePalette(
        "#E30A17", "#00B5E2", "#F8F9FA", "#FFFFFF", "#E5E7EB",
        "#111827", "#6B7280", "#10B981", "#B91C1C", "#6B7280",
    ),
    "dark": ThemePalette(
        "#E30A17", "#00B5E2", "#0F1115", "#1A1D23", "#2A2F38",
        "#E5E7EB", "#9CA3AF", "#10B981", "#DC2626", "#9CA3AF",
    ),
}


def get_palette(theme: str) -> ThemePalette:
    return PALETTES.get(theme, PALETTES["dark"])


# Mevcut çizim kodları için salt-okunur sözlük görünümü.
COLORS = {name: asdict(palette) for name, palette in PALETTES.items()}
