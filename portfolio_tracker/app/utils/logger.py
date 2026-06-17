import logging
import os
from logging.handlers import RotatingFileHandler

from app.config import LOGS_DIR


def setup_logger(name: str, log_file: str, level=logging.DEBUG) -> logging.Logger:
    """Belirtilen isimde ve dosyada log tutan bir logger döndürür."""
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Eğer logger'ın handler'ları varsa yeniden eklememek için kontrol
    if not logger.handlers:
        file_path = os.path.join(LOGS_DIR, log_file)

        # 5 MB sınır, maksimum 5 dosya rotasyonu
        handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=5)
        handler.setLevel(level)

        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        handler.setFormatter(formatter)

        # Geliştirme ortamında konsola da yazdır
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)

        logger.addHandler(handler)
        logger.addHandler(console_handler)

    return logger

app_logger = setup_logger("app", "app.log", level=logging.DEBUG)
prices_logger = setup_logger("prices", "prices.log", level=logging.INFO)
