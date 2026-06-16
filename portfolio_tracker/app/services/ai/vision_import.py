"""Görüntüden portföy aktarımı.

Kullanıcının portföy ekran görüntüsünü/fotoğrafını bir görüntü-anlayan (vision)
modele verip içindeki varlıkları yapılandırılmış listeye çevirir. Sonuç asla
otomatik kaydedilmez; kullanıcıya önizleme/onay için döndürülür.
"""

import os
from typing import Any, Dict, List

from app.services.ai.llm_provider import LLMError, LLMProvider, extract_json
from app.utils.logger import app_logger

_PROMPT = (
    "Bu görüntü bir yatırım portföyü ekranı veya tablosu. İçindeki her varlık "
    "için kodu, türünü, adedini ve ortalama maliyetini çıkar. SADECE şu şemada "
    "JSON döndür, açıklama yazma:\n"
    '{"holdings": [\n'
    '  {"code": "VARLIK KODU (büyük harf)", "type": "BIST veya TEFAS", '
    '"quantity": sayı, "avg_cost": sayı}\n'
    "]}\n"
    "Adet veya maliyet okunamıyorsa 0 yaz. BIST hisseleri genelde 4-5 harf, "
    "TEFAS fonları 2-3 harftir."
)

_MIME_BY_EXT = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
    ".bmp": "image/bmp",
}


def guess_mime(path: str) -> str:
    """Dosya uzantısından MIME türünü tahmin eder."""
    ext = os.path.splitext(path)[1].lower()
    return _MIME_BY_EXT.get(ext, "image/png")


def normalize_holdings(data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Model çıktısındaki ham varlık listesini güvenli biçime getirir."""
    holdings = data.get("holdings", []) if isinstance(data, dict) else []
    result: List[Dict[str, Any]] = []
    for h in holdings:
        if not isinstance(h, dict):
            continue
        code = str(h.get("code", "")).strip().upper()
        if not code or code == "NAN":
            continue
        a_type = str(h.get("type", "")).strip().upper()
        if a_type not in ("BIST", "TEFAS"):
            # Sezgi: 2-3 harf -> TEFAS, değilse BIST
            a_type = "TEFAS" if len(code) <= 3 else "BIST"

        def _num(v):
            try:
                return float(v)
            except (TypeError, ValueError):
                return 0.0

        result.append({
            "code": code,
            "type": a_type,
            "quantity": _num(h.get("quantity")),
            "avg_cost": _num(h.get("avg_cost")),
        })
    return result


def extract_holdings(
    provider: LLMProvider, image_bytes: bytes, mime_type: str
) -> List[Dict[str, Any]]:
    """Görüntüden varlık listesi çıkarır.

    Raises:
        LLMError: Sağlayıcı görüntü desteklemiyorsa ya da yanıt ayrıştırılamazsa.
    """
    raw = provider.analyze_image(
        image_bytes,
        mime_type,
        _PROMPT,
        system="Sen bir finansal tablo/ekran görüntüsü ayrıştırıcısısın. Sadece JSON döndür.",
    )
    data = extract_json(raw)
    if not data:
        app_logger.error(f"Görüntüden varlık çıkarılamadı. Ham yanıt: {raw}")
        raise LLMError(
            "Görüntüden varlıklar okunamadı. Daha net bir ekran görüntüsü deneyin."
        )
    return normalize_holdings(data)
