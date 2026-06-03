"""Doğal dilden işlem girişi.

Kullanıcının "Dün 100 THYAO aldım 280 liradan" gibi serbest metinlerini LLM
yardımıyla yapılandırılmış bir işlem sözlüğüne çevirir. Sonuç, kullanıcıya
onaylatılmak üzere ViewModel'e döndürülür (asla otomatik kaydedilmez).
"""

import datetime
from typing import Any, Dict, List, Optional

from app.services.ai.llm_provider import LLMError, LLMProvider, extract_json
from app.utils.logger import app_logger


def parse_transaction(
    provider: LLMProvider,
    text: str,
    today: Optional[datetime.date] = None,
    known_codes: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Serbest metni yapılandırılmış işlem verisine çevirir.

    Args:
        provider: Kullanılacak LLM sağlayıcısı.
        text: Kullanıcının yazdığı doğal dil ifadesi.
        today: Göreceli tarihler ("dün", "bugün") için referans tarih.
        known_codes: Portföyde tanımlı varlık kodları (eşleştirmeye yardımcı olur).

    Returns:
        ``{"asset_code", "tx_type", "date", "quantity", "unit_price",
        "commission", "note"}`` alanlarını içeren sözlük.

    Raises:
        LLMError: Model yanıtı ayrıştırılamazsa.
    """
    today = today or datetime.date.today()
    codes_hint = ""
    if known_codes:
        codes_hint = (
            "Portföyde tanımlı varlık kodları: "
            + ", ".join(known_codes)
            + ". Mümkünse bunlardan biriyle eşleştir.\n"
        )

    system = (
        "Sen bir finansal işlem ayrıştırıcısısın. Kullanıcının Türkçe ifadesini "
        "bir alım/satım işlemine çevirip SADECE JSON döndürürsün. Açıklama yazma."
    )
    prompt = (
        f"Bugünün tarihi: {today.isoformat()}.\n"
        f"{codes_hint}"
        f"Aşağıdaki ifadeyi şu JSON şemasına çevir:\n"
        "{\n"
        '  "asset_code": "varlık kodu (büyük harf, ör. THYAO)",\n'
        '  "tx_type": "BUY veya SELL",\n'
        '  "date": "YYYY-MM-DD",\n'
        '  "quantity": sayı,\n'
        '  "unit_price": sayı,\n'
        '  "commission": sayı (belirtilmemişse 0),\n'
        '  "note": "kısa not veya boş string"\n'
        "}\n"
        "Göreceli tarihleri (bugün, dün, geçen hafta) bugünün tarihine göre "
        "hesapla. Tutar belirtilmemişse unit_price 0 olsun.\n\n"
        f"İfade: {text}"
    )

    raw = provider.chat([{"role": "user", "content": prompt}], system=system)
    data = extract_json(raw)
    if not data:
        app_logger.error(f"İşlem ayrıştırılamadı. Ham yanıt: {raw}")
        raise LLMError("İfade anlaşılamadı. Lütfen daha açık bir şekilde yazın.")

    return _normalize(data, today)


def _normalize(data: Dict[str, Any], today: datetime.date) -> Dict[str, Any]:
    """Model çıktısını güvenli ve tutarlı bir biçime getirir."""
    code = str(data.get("asset_code", "")).strip().upper()
    tx_type = str(data.get("tx_type", "BUY")).strip().upper()
    if tx_type not in ("BUY", "SELL"):
        tx_type = "BUY"

    date_str = str(data.get("date", today.isoformat()))
    try:
        parsed_date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        parsed_date = today

    def _num(value: Any, default: float = 0.0) -> float:
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    return {
        "asset_code": code,
        "tx_type": tx_type,
        "date": parsed_date.isoformat(),
        "quantity": _num(data.get("quantity")),
        "unit_price": _num(data.get("unit_price")),
        "commission": _num(data.get("commission")),
        "note": str(data.get("note", "") or ""),
    }
