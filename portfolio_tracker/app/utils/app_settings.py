"""Uygulama ayarlarına merkezi erişim.

Ayarlar `settings` tablosunda anahtar-değer çiftleri olarak tutulur. Bu modül
varsayılan değerlerle veritabanındaki değerleri birleştirerek tek bir sözlük
döndürür. Hem ViewModel hem de servis katmanı buradan okur (MVVM'i bozmamak
için servisler genellikle sağlayıcıyı dışarıdan alır; bu modül yine de
viewmodel'lerin ortak varsayılanları paylaşması için kullanılır).
"""

from typing import Any, Dict

from app.database.session import get_session
from app.models.settings import Settings
from app.utils.logger import app_logger

# Tüm uygulama ayarlarının varsayılan değerleri (yapay zeka anahtarları dahil).
DEFAULT_SETTINGS: Dict[str, str] = {
    # Temel ayarlar
    "theme": "dark",
    "default_currency": "TRY",
    "refresh_interval_minutes": "15",
    "cost_method": "WAC",
    "notifications_enabled": "1",
    "language": "tr",
    # Yapay zeka ayarları
    # ai_provider: "none" | "ollama" | "gemini"
    "ai_provider": "none",
    # Ollama (yerel, tamamen ücretsiz) ayarları
    "ai_ollama_url": "http://localhost:11434",
    "ai_ollama_model": "llama3.1",
    # Google Gemini (ücretsiz katman, API anahtarı gerektirir) ayarları
    "ai_gemini_api_key": "",
    "ai_gemini_model": "gemini-1.5-flash",
}


def load_settings_dict() -> Dict[str, str]:
    """Varsayılanlarla veritabanındaki ayarları birleştirip döndürür."""
    settings_dict = DEFAULT_SETTINGS.copy()
    try:
        with get_session() as session:
            for row in session.query(Settings).all():
                if row.value is not None:
                    settings_dict[row.key] = row.value
    except Exception as e:  # pragma: no cover - veritabanı henüz hazır değilse
        app_logger.error(f"Ayarlar okunamadı: {e}")
    return settings_dict


def get_setting(key: str, default: Any = None) -> Any:
    """Tek bir ayar değerini döndürür."""
    return load_settings_dict().get(key, default)
