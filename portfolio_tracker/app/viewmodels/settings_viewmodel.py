from PySide6.QtCore import QObject, Signal
from app.database.session import get_session
from app.models.settings import Settings
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.models.alert import Alert
from app.models.price_history import PriceHistory
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.import_export_service import ImportExportService
from app.services.backup_service import BackupService
from app.utils.logger import app_logger

class SettingsViewModel(QObject):
    settings_loaded = Signal(dict)
    settings_saved = Signal()
    error_occurred = Signal(str)
    success_message = Signal(str)
    data_wiped = Signal()
    data_changed = Signal()                 # import sonrası portföyü tazele
    percentage_import_needed = Signal(str)  # (dosya yolu) — toplam değer sorulmalı

    default_settings = {
        "theme": "system",
        "default_currency": "TRY",
        "refresh_interval_minutes": "15",
        "cost_method": "WAC",
        "notifications_enabled": "1",
    }

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

    def export_data(self, file_path: str, columns=None, portfolio_items=None):
        try:
            with get_session() as session:
                ImportExportService.export_excel(
                    session, file_path, portfolio_items=portfolio_items, columns=columns
                )
            self.success_message.emit("Dışa aktarma işlemi başarıyla tamamlandı.")
        except Exception as e:
            self.error_occurred.emit(f"Dışa aktarma hatası: {str(e)}")

    def import_data(self, file_path: str):
        # Yüzdelik senaryosu toplam değer gerektirir; view'a sinyal gönderilir.
        try:
            if ImportExportService.detect_percentage(file_path):
                self.percentage_import_needed.emit(file_path)
                return
        except Exception as e:
            self.error_occurred.emit(f"İçeri aktarma hatası: {str(e)}")
            return

        try:
            with get_session() as session:
                success = ImportExportService.import_excel(session, file_path)
            if success:
                self.success_message.emit("İçeri aktarma işlemi başarıyla tamamlandı.")
                self.data_changed.emit()
            else:
                self.error_occurred.emit("İçeri aktarma sırasında uygun veri formatı bulunamadı.")
        except Exception as e:
            self.error_occurred.emit(f"İçeri aktarma hatası: {str(e)}")

    def import_percentage(self, file_path: str, total_value: float):
        try:
            with get_session() as session:
                success = ImportExportService.import_percentage(session, file_path, total_value)
            if success:
                self.success_message.emit("Yüzdelik portföy başarıyla içeri aktarıldı.")
                self.data_changed.emit()
            else:
                self.error_occurred.emit("Yüzdelik içeri aktarma başarısız oldu.")
        except Exception as e:
            self.error_occurred.emit(f"Yüzdelik içeri aktarma hatası: {str(e)}")

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

    def delete_all_data(self):
        """Tüm portföy verisini siler. Güvenlik için önce otomatik yedek alınır."""
        try:
            # Silmeden önce güvenlik yedeği
            BackupService.create_backup()
            with get_session() as session:
                # Sıra önemli değil (cascade var) ama açıkça temizleyelim
                session.query(Alert).delete()
                session.query(Transaction).delete()
                session.query(PriceHistory).delete()
                session.query(PortfolioSnapshot).delete()
                session.query(Asset).delete()
                session.commit()
            self.success_message.emit("Tüm veri silindi. (Silmeden önce otomatik yedek alındı.)")
            self.data_wiped.emit()
        except Exception as e:
            app_logger.error(f"Veri silme hatası: {e}")
            self.error_occurred.emit(f"Veri silme hatası: {str(e)}")
