"""Uygulama fontlarını (Inter + JetBrains Mono) yükler.

QSS dosyaları "Inter" ve "JetBrains Mono" font ailelerini kullanır. Bu fontlar
`app/resources/fonts/` altında gömülüdür ve açılışta QFontDatabase'e eklenir.
Dosyalar yoksa sistem fontuna düşülür (sessiz).
"""

import os

from PySide6.QtGui import QFont, QFontDatabase

from app.config import ROOT_DIR
from app.utils.logger import app_logger

FONTS_DIR = os.path.join(str(ROOT_DIR), "app", "resources", "fonts")


def load_fonts() -> bool:
    """fonts klasöründeki tüm .ttf/.otf dosyalarını yükler.

    Returns:
        "Inter" ailesi başarıyla yüklendiyse True.
    """
    inter_loaded = False
    if not os.path.isdir(FONTS_DIR):
        app_logger.info(f"Font klasörü bulunamadı: {FONTS_DIR}")
        return False

    for name in sorted(os.listdir(FONTS_DIR)):
        if not name.lower().endswith((".ttf", ".otf")):
            continue
        path = os.path.join(FONTS_DIR, name)
        font_id = QFontDatabase.addApplicationFont(path)
        if font_id == -1:
            app_logger.warning(f"Font yüklenemedi: {name}")
            continue
        families = QFontDatabase.applicationFontFamilies(font_id)
        if any("Inter" in f for f in families):
            inter_loaded = True

    return inter_loaded


def apply_default_font(app, family: str = "Inter", size: int = 10) -> None:
    """Uygulama genel fontunu ayarlar (aile mevcutsa)."""
    available = QFontDatabase.families()
    if family in available:
        app.setFont(QFont(family, size))
