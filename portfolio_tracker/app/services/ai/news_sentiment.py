"""Haber başlıklarından duygu (sentiment) analizi.

Bir varlık (BIST hissesi) hakkındaki güncel haber başlıklarını Google News'in
RSS akışından çeker ve seçilen LLM ile pozitif/negatif/nötr duygu skoru üretir.
Bulut sağlayıcılarının fiyat ve kota koşulları değişebilir.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List
from urllib.parse import quote

import httpx

from app.services.ai.llm_provider import LLMError, LLMProvider, extract_json
from app.utils.logger import app_logger

GOOGLE_NEWS_RSS = "https://news.google.com/rss/search?q={query}&hl=tr&gl=TR&ceid=TR:tr"


def fetch_headlines(query: str, limit: int = 8) -> List[str]:
    """Verilen sorgu için güncel haber başlıklarını döndürür.

    Args:
        query: Arama sorgusu (ör. "THYAO hisse" veya şirket adı).
        limit: En fazla kaç başlık döndürüleceği.

    Returns:
        Başlık metinlerinin listesi (hata durumunda boş liste).
    """
    url = GOOGLE_NEWS_RSS.format(query=quote(query))
    try:
        resp = httpx.get(url, timeout=15.0, follow_redirects=True)
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        titles: List[str] = []
        for item in root.iter("item"):
            title_el = item.find("title")
            if title_el is not None and title_el.text:
                titles.append(title_el.text.strip())
            if len(titles) >= limit:
                break
        return titles
    except Exception as e:
        app_logger.error(f"Haber başlıkları çekilemedi ({query}): {e}")
        return []


def analyze_sentiment(
    provider: LLMProvider, asset_name: str, headlines: List[str]
) -> Dict[str, Any]:
    """Başlıkları LLM ile analiz edip duygu skoru üretir.

    Args:
        provider: LLM sağlayıcısı.
        asset_name: Varlık adı/kodu (istemde bağlam için).
        headlines: Analiz edilecek haber başlıkları.

    Returns:
        ``{"sentiment": "pozitif"|"negatif"|"nötr", "score": -1..1,
        "summary": str}`` sözlüğü.

    Raises:
        LLMError: Yanıt ayrıştırılamazsa.
    """
    if not headlines:
        return {
            "sentiment": "nötr",
            "score": 0.0,
            "summary": "Güncel haber başlığı bulunamadı.",
        }

    joined = "\n".join(f"- {h}" for h in headlines)
    system = (
        "Sen bir finansal haber duygu analisti olarak çalışıyorsun. Sana verilen "
        "haber başlıklarını değerlendirip SADECE JSON döndürürsün."
    )
    prompt = (
        f"'{asset_name}' varlığı hakkındaki şu haber başlıklarını değerlendir:\n"
        f"{joined}\n\n"
        "Şu JSON şemasıyla yanıt ver:\n"
        "{\n"
        '  "sentiment": "pozitif | negatif | nötr",\n'
        '  "score": -1 ile 1 arası bir sayı,\n'
        '  "summary": "1-2 cümlelik Türkçe özet"\n'
        "}"
    )

    raw = provider.chat([{"role": "user", "content": prompt}], system=system)
    data = extract_json(raw)
    if not data:
        app_logger.error(f"Duygu analizi ayrıştırılamadı. Ham yanıt: {raw}")
        raise LLMError("Haber analizi yorumlanamadı.")

    sentiment = str(data.get("sentiment", "nötr")).strip().lower()
    if sentiment not in ("pozitif", "negatif", "nötr"):
        sentiment = "nötr"
    try:
        score = max(-1.0, min(1.0, float(data.get("score", 0.0))))
    except (TypeError, ValueError):
        score = 0.0

    return {
        "sentiment": sentiment,
        "score": score,
        "summary": str(data.get("summary", "")),
        "headlines": headlines,
    }
