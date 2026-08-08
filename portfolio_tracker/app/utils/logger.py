import logging
import os
import re
from collections.abc import Iterable
from logging.handlers import RotatingFileHandler

from app.config import LOGS_DIR

_REGISTERED_SECRETS: set[str] = set()
_MASK = "[REDACTED]"
_SENSITIVE_PATTERNS = (
    re.compile(r"(?i)(x-goog-api-key\s*[:=]\s*)[^\s,;]+"),
    re.compile(r"(?i)(authorization\s*[:=]\s*bearer\s+)[^\s,;]+"),
    re.compile(r"(?i)([?&]key=)[^&\s]+"),
    re.compile(r"(?i)(api[_-]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s,;}]+"),
    re.compile(r"AIza[0-9A-Za-z_-]{20,}"),
)


def register_secret(secret: str) -> None:
    """Bilinen bir sırrı, bütün log handler'ları için maskelenecek listeye ekler."""
    if len(secret) >= 4:
        _REGISTERED_SECRETS.add(secret)


def redact_sensitive(value: object, extra_secrets: Iterable[str] = ()) -> str:
    """Anahtarları URL, header, hata cevabı ve serbest metinden temizler."""
    text = str(value)
    for pattern in _SENSITIVE_PATTERNS:
        text = pattern.sub(lambda match: (match.group(1) if match.lastindex else "") + _MASK, text)
    for secret in (*_REGISTERED_SECRETS, *extra_secrets):
        if secret:
            text = text.replace(secret, _MASK)
    return text


class SensitiveDataFilter(logging.Filter):
    """LogRecord biçimlendirilmeden önce hassas verileri maskeler."""

    def filter(self, record: logging.LogRecord) -> bool:
        record.msg = redact_sensitive(record.getMessage())
        record.args = ()
        return True


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

        formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        sensitive_filter = SensitiveDataFilter()
        handler.addFilter(sensitive_filter)
        handler.setFormatter(formatter)

        # Geliştirme ortamında konsola da yazdır
        console_handler = logging.StreamHandler()
        console_handler.setLevel(level)
        console_handler.setFormatter(formatter)
        console_handler.addFilter(sensitive_filter)

        logger.addHandler(handler)
        logger.addHandler(console_handler)

    return logger

app_logger = setup_logger("app", "app.log", level=logging.DEBUG)
prices_logger = setup_logger("prices", "prices.log", level=logging.INFO)
