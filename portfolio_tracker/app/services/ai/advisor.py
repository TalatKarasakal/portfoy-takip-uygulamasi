"""Hedef bazlı öneri / yeniden dengeleme motoru.

Portföyün güncel durumunu, deterministik risk bulgularını ve (varsa) teknik
indikatör sinyallerini birleştirip LLM'den okunabilir, hedefe yönelik öneriler
üretmesini ister. Öneriler bilgilendirme amaçlıdır.
"""

from typing import Any, Dict, List, Optional

from app.services.ai.llm_provider import LLMProvider
from app.services.ai.portfolio_context import build_portfolio_context
from app.services.ai.risk_analyzer import analyze_risk, PROFILE_LABELS


def generate_advice(
    provider: LLMProvider,
    portfolio_items: List[Dict[str, Any]],
    kpi_data: Dict[str, Any],
    goal: str = "",
    indicator_summaries: Optional[Dict[str, str]] = None,
    profile: str = "balanced",
) -> str:
    """Portföy için doğal dilde öneri metni üretir.

    Args:
        provider: LLM sağlayıcısı.
        portfolio_items: Pozisyon sözlükleri.
        kpi_data: Toplam değer/maliyet/K-Z bilgisi.
        goal: Kullanıcının serbest metin hedefi (ör. "uzun vade, düşük risk").
        indicator_summaries: ``{kod: trend_açıklaması}`` biçiminde teknik özetler.

    Returns:
        LLM tarafından üretilen Türkçe öneri metni.
    """
    context = build_portfolio_context(portfolio_items, kpi_data)
    risk_warnings = analyze_risk(portfolio_items, profile=profile)

    parts: List[str] = [context, ""]
    parts.append(f"Yatırımcı profili: {PROFILE_LABELS.get(profile, 'Dengeli')}")
    parts.append("")

    if risk_warnings:
        parts.append("=== TESPİT EDİLEN RİSKLER ===")
        for w in risk_warnings:
            parts.append(f"- [{w['severity']}] {w['title']}: {w['message']}")
        parts.append("")

    if indicator_summaries:
        parts.append("=== TEKNİK GÖSTERGELER ===")
        for code, summary in indicator_summaries.items():
            parts.append(f"- {code}: {summary}")
        parts.append("")

    goal_text = goal.strip() or "belirtilmedi (genel değerlendirme yap)"
    parts.append(f"=== KULLANICININ HEDEFİ ===\n{goal_text}")

    system = (
        "Sen deneyimli bir Türkçe portföy danışmanısın. Sana verilen portföy "
        "verisi, risk bulguları ve teknik göstergelere dayanarak kullanıcının "
        "hedefine uygun, somut ve uygulanabilir öneriler sunarsın. Önerilerini "
        "madde madde, kısa ve net yaz. Sadece verilen veriye dayan, uydurma."
    )
    prompt = (
        "Aşağıdaki bilgilere göre portföy için yeniden dengeleme ve iyileştirme "
        "önerileri hazırla. Konsantrasyon, çeşitlendirme ve hedefe uygunluğu "
        "değerlendir:\n\n" + "\n".join(parts)
    )

    return provider.chat([{"role": "user", "content": prompt}], system=system)
