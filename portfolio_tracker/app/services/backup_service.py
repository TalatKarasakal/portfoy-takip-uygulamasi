import shutil
import os
import glob
from datetime import datetime
from app.config import DATABASE_FILE, BACKUP_DIR
from app.utils.logger import app_logger

class BackupService:
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
