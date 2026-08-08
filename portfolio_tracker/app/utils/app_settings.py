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

CLOUD_CONSENT_VERSION = "2026-08-v1"
CLOUD_DATA_FIELDS = (
    "varlık kodu ve türü",
    "adet, maliyet ve güncel değer",
    "portföy toplamları ve performans göstergeleri",
    "kullanıcının yazdığı mesaj veya yüklediği görüntü",
)

# API anahtarları bu sözlükte veya SQLite'ta tutulmaz.
DEFAULT_SETTINGS: Dict[str, str] = {
    # Temel ayarlar
    "theme": "system",
    "default_currency": "TRY",
    "refresh_interval_minutes": "15",
    "cost_method": "WAC",
    "notifications_enabled": "1",
    # Yatırımcı risk profili: "conservative" | "balanced" | "aggressive"
    "risk_profile": "balanced",
    # Yapay zeka ayarları
    # ai_provider: "none" | "ollama" | "local" | "gemini"
    "ai_provider": "none",
    # Ollama (yerel, tamamen ücretsiz) ayarları
    "ai_ollama_url": "http://localhost:11434",
    "ai_ollama_model": "llama3.1",
    # OpenAI-uyumlu yerel sunucu (LM Studio, llama.cpp, Jan, vLLM vb.) ayarları
    "ai_local_url": "http://localhost:1234/v1",
    "ai_local_model": "",
    "ai_local_api_key": "",
    # Google Gemini (fiyat/kota sağlayıcı koşullarına bağlıdır)
    "ai_gemini_model": "gemini-2.0-flash",
    "ai_cloud_consent_version": "",
}


def load_settings_dict() -> Dict[str, str]:
    """Varsayılanlarla veritabanındaki ayarları birleştirip döndürür."""
    settings_dict = DEFAULT_SETTINGS.copy()
    try:
        with get_session() as session:
            for row in session.query(Settings).all():
                if row.key == "ai_gemini_api_key":
                    continue
                if row.value is not None:
                    settings_dict[row.key] = row.value
    except Exception as e:  # pragma: no cover - veritabanı henüz hazır değilse
        app_logger.error(f"Ayarlar okunamadı: {e}")
    return settings_dict


def get_setting(key: str, default: Any = None) -> Any:
    """Tek bir ayar değerini döndürür."""
    return load_settings_dict().get(key, default)
