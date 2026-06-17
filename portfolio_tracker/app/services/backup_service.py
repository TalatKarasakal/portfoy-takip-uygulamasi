import glob
import os
import shutil
from datetime import datetime, timedelta

from app.config import BACKUP_DIR, DATABASE_FILE
from app.utils.logger import app_logger


class BackupService:
    @staticmethod
    def maybe_auto_backup(days: int = 7) -> bool:
        """Son yedekten `days` günden fazla geçtiyse otomatik yedek alır.

        Son yedek tarihi `settings` tablosundaki `last_backup_date` anahtarından
        okunur/yazılır. Açılışta çağrılması beklenir.
        """
        try:
            # Geç import: model registry ve session hazır olduktan sonra
            from app.database.session import get_session
            from app.models.settings import Settings

            with get_session() as session:
                row = session.query(Settings).filter_by(key="last_backup_date").first()
                last_str = row.value if row else None
                needs = True
                if last_str:
                    try:
                        last = datetime.strptime(last_str, "%Y-%m-%d")
                        needs = (datetime.now() - last) >= timedelta(days=days)
                    except ValueError:
                        needs = True

                if not needs:
                    return False

                if BackupService.create_backup():
                    today = datetime.now().strftime("%Y-%m-%d")
                    if row:
                        row.value = today
                    else:
                        session.add(Settings(key="last_backup_date", value=today))
                    session.commit()
                    return True
            return False
        except Exception as e:
            app_logger.error(f"Otomatik yedek başarısız: {e}")
            return False

    @staticmethod
    def create_backup() -> bool:
        """Portföy veritabanını yedekler ve rotasyon yönetir."""
        if not os.path.exists(DATABASE_FILE):
            app_logger.warning("Veritabanı dosyası bulunamadığı için yedek alınamadı.")
            return False

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = os.path.join(BACKUP_DIR, f"backup_{timestamp}.db")

        try:
            shutil.copy2(DATABASE_FILE, backup_file)
            app_logger.info(f"Database backed up successfully to {backup_file}")

            # Rotasyon (Maks 10 dosya tut)
            backups = glob.glob(os.path.join(BACKUP_DIR, "backup_*.db"))
            if len(backups) > 10:
                # Dosya isimleri tarihe göre sıralanabilir
                backups.sort()
                for i in range(len(backups) - 10):
                    os.remove(backups[i])
                    app_logger.info(f"Eski yedek silindi: {backups[i]}")

            return True
        except Exception as e:
            app_logger.error(f"Yedekleme başarısız: {e}")
            return False

    @staticmethod
    def restore_backup(backup_file_path: str) -> bool:
        """Seçilen yedek dosyasından veritabanını geri yükler."""
        if not os.path.exists(backup_file_path):
            app_logger.error(f"Geri yükleme için dosya bulunamadı: {backup_file_path}")
            return False

        try:
            # Önce aktif db'nin anlık kopyasını güvenli yedek olarak al
            temp_safety = os.path.join(BACKUP_DIR, "temp_safety_before_restore.db")
            if os.path.exists(DATABASE_FILE):
                shutil.copy2(DATABASE_FILE, temp_safety)

            shutil.copy2(backup_file_path, DATABASE_FILE)
            app_logger.info(f"Database successfully restored from {backup_file_path}")
            return True
        except Exception as e:
            app_logger.error(f"Geri yükleme başarısız: {e}")
            return False
