import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication

from app.database.engine import init_db
from app.services.backup_service import BackupService
from app.utils.logger import app_logger
from app.views.main_window import MainWindow
from mac_identity import set_dock_icon, set_dock_name

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")


def main():
    # macOS Dock adını GUI başlamadan önce ayarlamayı dene ("python" yerine).
    set_dock_name("Portföy Takip")

    # İlk kullanım için veritabanını ilklendir
    init_db()

    # Açılışta otomatik yedek (son yedekten 7 gün geçtiyse)
    try:
        BackupService.maybe_auto_backup()
    except Exception as e:
        app_logger.error(f"Açılış yedeği atlandı: {e}")

    app = QApplication(sys.argv)
    app.setApplicationName("Portföy Takip ve Analiz")
    app.setApplicationDisplayName("Portföy Takip")
    app.setOrganizationName("PortfolioTracker")
    app.setWindowIcon(QIcon(_ICON_PATH))
    # Dock simgesini çalışma anında ayarla (python ile açınca da görünür).
    set_dock_icon(_ICON_PATH)

    # Gömülü fontları yükle (Inter + JetBrains Mono)
    try:
        from app.utils.fonts import apply_default_font, load_fonts
        load_fonts()
        apply_default_font(app, "Inter", 10)
    except Exception as e:
        app_logger.error(f"Font yükleme atlandı: {e}")

    # Varsayılan temel stili uygula (tema QSS'i üzerine binecek)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
