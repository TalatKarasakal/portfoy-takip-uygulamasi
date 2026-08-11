"""Tema ile uyumlu uygulama simgesi seçimi."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QWidget

from app.config import ROOT_DIR
from mac_identity import set_dock_icon

_ICON_DIR = Path(ROOT_DIR) / "app" / "resources"
_THEME_ICONS = {
    "light": _ICON_DIR / "app_icon_light.png",
    "dark": _ICON_DIR / "app_icon_dark.png",
}
_FALLBACK_ICON = _ICON_DIR / "app_icon.png"


def icon_path_for_theme(theme: str) -> Path:
    """Tema simgesini, eksik kaynakta şeffaf master'a dönerek seç."""
    path = _THEME_ICONS.get(theme, _FALLBACK_ICON)
    return path if path.is_file() else _FALLBACK_ICON


def apply_application_icon(theme: str, window: QWidget | None = None) -> Path:
    """Qt pencere/görev çubuğu ve macOS Dock simgesini birlikte güncelle."""
    path = icon_path_for_theme(theme)
    icon = QIcon(str(path))
    if not icon.isNull():
        app = QApplication.instance()
        if isinstance(app, QApplication):
            app.setWindowIcon(icon)
        if window is not None:
            window.setWindowIcon(icon)
        set_dock_icon(str(path))
    return path
