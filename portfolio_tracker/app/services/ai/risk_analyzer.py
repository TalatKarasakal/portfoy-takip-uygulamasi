"""Akıllı risk ve çeşitlendirme analizi.

Bu modülün çekirdeği tamamen deterministiktir (LLM gerektirmez) ve bu sayede
birim testlerle doğrulanabilir. Konsantrasyon riski, varlık sınıfı yığılması ve
yetersiz çeşitlendirme gibi durumları tespit eder. İsteğe bağlı olarak bu
bulgular bir LLM'e verilerek doğal dilde yorum üretilebilir.
"""

from typing import Any, Dict, List

# Eşik değerleri (portföy yüzdesi olarak)
SINGLE_POSITION_HIGH = 40.0
SINGLE_POSITION_MEDIUM = 25.0
ASSET_TYPE_HIGH = 85.0
MIN_POSITIONS = 4


def analyze_risk(portfolio_items: List[Dict[str, Any]]) -> List[Dict[str, str]]:
    """Portföyü tarayıp risk uyarıları üretir.

    Args:
        portfolio_items: ``PortfolioViewModel`` pozisyon sözlükleri.

    Returns:
        ``{"severity": "high"|"medium"|"info", "title": str, "message": str}``
        biçiminde uyarı sözlükleri listesi. Uyarı yoksa boş liste döner.
    """
    warnings: List[Dict[str, str]] = []
    if not portfolio_items:
        return warnings

    total_value = sum(item.get("current_value", 0) for item in portfolio_items)
    if total_value <= 0:
        return warnings

    # 1) Tek pozisyon konsantrasyonu
    for item in portfolio_items:
        pct = item.get("current_value", 0) / total_value * 100
        if pct >= SINGLE_POSITION_HIGH:
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
        elif pct >= SINGLE_POSITION_MEDIUM:
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
        if pct >= ASSET_TYPE_HIGH and len(type_totals) > 1:
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
    if len(portfolio_items) < MIN_POSITIONS:
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
