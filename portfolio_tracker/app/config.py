import os
import sys
from pathlib import Path

# Projenin kök dizini
if getattr(sys, 'frozen', False):
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
COLORS = {
    "light": {
        "primary": "#E30A17",
        "secondary": "#00B5E2",
        "background": "#F8F9FA",
        "surface": "#FFFFFF",
        "border": "#E5E7EB",
        "text_primary": "#111827",
        "text_secondary": "#6B7280",
        "profit": "#10B981",
        "loss": "#B91C1C",
        "neutral": "#6B7280",
    },
    "dark": {
        "primary": "#E30A17",
        "secondary": "#00B5E2",
        "background": "#0F1115",
        "surface": "#1A1D23",
        "border": "#2A2F38",
        "text_primary": "#E5E7EB",
        "text_secondary": "#9CA3AF",
        "profit": "#10B981",
        "loss": "#DC2626",
        "neutral": "#9CA3AF",
    }
}
