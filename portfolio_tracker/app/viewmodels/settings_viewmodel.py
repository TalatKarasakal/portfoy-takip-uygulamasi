from PySide6.QtCore import QObject, Signal
from app.database.session import get_session
from app.models.settings import Settings
from app.services.import_export_service import ImportExportService
from app.services.backup_service import BackupService
from app.utils.app_settings import DEFAULT_SETTINGS

class SettingsViewModel(QObject):
    settings_loaded = Signal(dict)
    settings_saved = Signal()
    error_occurred = Signal(str)
    success_message = Signal(str)

    # Yapay zeka anahtarları dahil tüm varsayılanlar app_settings'te tutulur
    default_settings = DEFAULT_SETTINGS

    def load_settings(self):
        try:
            with get_session() as session:
                db_settings = session.query(Settings).all()
                settings_dict = self.default_settings.copy()
                for s in db_settings:
                    settings_dict[s.key] = s.value
                self.settings_loaded.emit(settings_dict)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def save_settings(self, new_settings: dict):
        try:
            with get_session() as session:
                for k, v in new_settings.items():
                    s = session.query(Settings).filter_by(key=k).first()
                    if s:
                        s.value = str(v)
                    else:
                        session.add(Settings(key=k, value=str(v)))
                session.commit()
            self.settings_saved.emit()
            self.load_settings()
        except Exception as e:
            self.error_occurred.emit(str(e))

    def export_data(self, file_path: str):
        try:
            with get_session() as session:
                ImportExportService.export_excel(session, file_path)
            self.success_message.emit("Dışa aktarma işlemi başarıyla tamamlandı.")
        except Exception as e:
            self.error_occurred.emit(f"Dışa aktarma hatası: {str(e)}")

    def import_data(self, file_path: str):
        try:
            with get_session() as session:
                success = ImportExportService.import_excel(session, file_path)
            if success:
                self.success_message.emit("İçeri aktarma işlemi başarıyla tamamlandı.")
            else:
                self.error_occurred.emit("İçeri aktarma sırasında veri format hatası oluştu.")
        except Exception as e:
            self.error_occurred.emit(f"İçeri aktarma hatası: {str(e)}")

    def create_backup(self):
        try:
            if BackupService.create_backup():
                self.success_message.emit("Veritabanı yedeği başarıyla alındı.")
            else:
                self.error_occurred.emit("Yedek alınamadı.")
        except Exception as e:
            self.error_occurred.emit(f"Yedekleme hatası: {str(e)}")

    def restore_backup(self, path: str):
        try:
            if BackupService.restore_backup(path):
                self.success_message.emit("Veritabanı başarıyla geri yüklendi. Uygulamayı yeniden başlatın.")
            else:
                self.error_occurred.emit("Geri yükleme başarısız oldu.")
        except Exception as e:
            self.error_occurred.emit(f"Geri yükleme hatası: {str(e)}")
