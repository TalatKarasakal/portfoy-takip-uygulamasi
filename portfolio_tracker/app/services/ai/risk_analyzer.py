"""Akıllı risk ve çeşitlendirme analizi.

Bu modülün çekirdeği tamamen deterministiktir (LLM gerektirmez) ve bu sayede
birim testlerle doğrulanabilir. Konsantrasyon riski, varlık sınıfı yığılması ve
yetersiz çeşitlendirme gibi durumları tespit eder. İsteğe bağlı olarak bu
bulgular bir LLM'e verilerek doğal dilde yorum üretilebilir.
"""

from typing import Any, Dict, List

# Varsayılan (Dengeli) eşik değerleri (portföy yüzdesi olarak)
SINGLE_POSITION_HIGH = 40.0
SINGLE_POSITION_MEDIUM = 25.0
ASSET_TYPE_HIGH = 85.0
MIN_POSITIONS = 4

# Yatırımcı profiline göre eşikler. Temkinli profil daha düşük eşiklerle daha
# hassas uyarır; Atak profil daha yüksek eşiklerle daha az uyarır.
PROFILE_THRESHOLDS: Dict[str, Dict[str, float]] = {
    "conservative": {
        "single_high": 25.0, "single_medium": 15.0,
        "type_high": 70.0, "min_positions": 6,
    },
    "balanced": {
        "single_high": SINGLE_POSITION_HIGH, "single_medium": SINGLE_POSITION_MEDIUM,
        "type_high": ASSET_TYPE_HIGH, "min_positions": MIN_POSITIONS,
    },
    "aggressive": {
        "single_high": 55.0, "single_medium": 40.0,
        "type_high": 95.0, "min_positions": 3,
    },
}

PROFILE_LABELS = {
    "conservative": "Temkinli",
    "balanced": "Dengeli",
    "aggressive": "Atak",
}


def analyze_risk(
    portfolio_items: List[Dict[str, Any]], profile: str = "balanced"
) -> List[Dict[str, str]]:
    """Portföyü tarayıp risk uyarıları üretir.

    Args:
        portfolio_items: ``PortfolioViewModel`` pozisyon sözlükleri.
        profile: Yatırımcı profili ("conservative"|"balanced"|"aggressive").
            Eşik değerlerini ayarlar.

    Returns:
        ``{"severity": "high"|"medium"|"info", "title": str, "message": str}``
        biçiminde uyarı sözlükleri listesi. Uyarı yoksa boş liste döner.
    """
    th = PROFILE_THRESHOLDS.get(profile, PROFILE_THRESHOLDS["balanced"])
    single_high = th["single_high"]
    single_medium = th["single_medium"]
    type_high = th["type_high"]
    min_positions = th["min_positions"]

    warnings: List[Dict[str, str]] = []
    if not portfolio_items:
        return warnings

    total_value = sum(item.get("current_value", 0) for item in portfolio_items)
    if total_value <= 0:
        return warnings

    # 1) Tek pozisyon konsantrasyonu
    for item in portfolio_items:
        pct = item.get("current_value", 0) / total_value * 100
        if pct >= single_high:
            warnings.append(
                {
                    "severity": "high",
                    "title": "Yüksek Konsantrasyon Riski",
                    "message": (
                        f"Portföyünün %{pct:.1f}'i tek bir varlıkta ({item['code']}) "
                        f"toplanmış. Bu, riski tek bir varlığa bağlar."
                    ),
                }
            )
        elif pct >= single_medium:
            warnings.append(
                {
                    "severity": "medium",
                    "title": "Konsantrasyon Uyarısı",
                    "message": (
                        f"{item['code']} portföyünün %{pct:.1f}'ini oluşturuyor. "
                        f"Çeşitlendirmeyi gözden geçirebilirsin."
                    ),
                }
            )

    # 2) Varlık sınıfı yığılması (BIST vs TEFAS)
    type_totals: Dict[str, float] = {}
    for item in portfolio_items:
        type_totals[item["type"]] = type_totals.get(item["type"], 0.0) + item.get(
            "current_value", 0
        )
    for asset_type, value in type_totals.items():
        pct = value / total_value * 100
        if pct >= type_high and len(type_totals) > 1:
            warnings.append(
                {
                    "severity": "medium",
                    "title": "Varlık Sınıfı Yığılması",
                    "message": (
                        f"Portföyünün %{pct:.1f}'i {asset_type} sınıfında. Sınıflar "
                        f"arası dengeyi gözden geçirebilirsin."
                    ),
                }
            )

    # 3) Yetersiz çeşitlendirme
    if len(portfolio_items) < min_positions:
        warnings.append(
            {
                "severity": "info",
                "title": "Sınırlı Çeşitlendirme",
                "message": (
                    f"Portföyünde {len(portfolio_items)} pozisyon var. Daha geniş "
                    f"çeşitlendirme riski azaltabilir."
                ),
            }
        )

    return warnings


def build_risk_summary_prompt(warnings: List[Dict[str, str]]) -> str:
    """Risk bulgularını LLM yorumu için istem metnine çevirir."""
    if not warnings:
        return (
            "Portföyde belirgin bir konsantrasyon ya da çeşitlendirme riski "
            "tespit edilmedi. Kullanıcıyı kısaca bilgilendir."
        )
    lines = ["Aşağıdaki risk bulgularını kısa ve sade bir Türkçe paragrafla yorumla:"]
    for w in warnings:
        lines.append(f"- [{w['severity']}] {w['title']}: {w['message']}")
    return "\n".join(lines)
