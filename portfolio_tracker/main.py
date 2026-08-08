import os
import sys

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from app.database.engine import engine, init_db
from app.database.migration_service import MigrationError, MigrationService
from app.services.backup_service import BackupService
from app.utils.logger import app_logger
from app.views.main_window import MainWindow
from mac_identity import set_dock_icon, set_dock_name

_ICON_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "app_icon.png")


def main():
    # macOS Dock adını GUI başlamadan önce ayarlamayı dene ("python" yerine).
    set_dock_name("Portföy Takip")

    app = QApplication(sys.argv)
    app.setApplicationName("Portföy Takip ve Analiz")
    app.setApplicationDisplayName("Portföy Takip")
    app.setOrganizationName("PortfolioTracker")
    app.setWindowIcon(QIcon(_ICON_PATH))

    # Şema değişikliği mevcut kullanıcı verisine uygulanmadan önce açık onay al.
    try:
        migration_plan = MigrationService.inspect_plan(engine)
        approved = not migration_plan.requires_backup
        if migration_plan.requires_backup:
            answer = QMessageBox.question(
                None,
                "Veritabanı Güncellemesi",
                migration_plan.summary
                + "\n\nİşlemden önce doğrulanmış güvenlik yedeği alınacak. Devam edilsin mi?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            approved = answer == QMessageBox.Yes
        if not approved:
            return
        init_db(migration_approved=approved)
    except MigrationError as exc:
        app_logger.critical("Veritabanı hazırlanamadı: %s", exc)
        QMessageBox.critical(None, "Veritabanı Hatası", str(exc))
        return

    # Açılışta otomatik yedek (son yedekten 7 gün geçtiyse)
    try:
        BackupService.maybe_auto_backup()
    except Exception as e:
        app_logger.error(f"Açılış yedeği atlandı: {e}")

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
