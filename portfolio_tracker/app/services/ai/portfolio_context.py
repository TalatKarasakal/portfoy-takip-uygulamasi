"""Portföy verisini LLM'e verilecek Türkçe bağlam metnine dönüştürür.

LLM'in portföy hakkında sorulara cevap verebilmesi için güncel pozisyonların,
kâr/zarar durumunun ve dağılımın okunabilir bir özetine ihtiyacı var. Bu modül,
``PortfolioViewModel`` tarafından zaten hesaplanmış olan veriyi (yeniden fiyat
çekmeden) düz metne çevirir.
"""

from typing import Any, Dict, List

from app.utils.formatters import format_currency, format_percent


def build_portfolio_context(
    portfolio_items: List[Dict[str, Any]], kpi_data: Dict[str, Any]
) -> str:
    """Portföyün güncel durumunu özetleyen Türkçe metin üretir.

    Args:
        portfolio_items: ``PortfolioViewModel`` pozisyon sözlükleri listesi.
        kpi_data: Toplam değer, maliyet ve K/Z bilgilerini içeren sözlük.

    Returns:
        LLM'e bağlam olarak verilecek Türkçe özet metin.
    """
    if not portfolio_items:
        return "Kullanıcının portföyünde şu anda kayıtlı bir pozisyon yok."

    lines: List[str] = []
    lines.append("=== PORTFÖY ÖZETİ ===")
    lines.append(f"Toplam Değer: {format_currency(kpi_data.get('total_value_try', 0))}")
    lines.append(
        f"Toplam Maliyet: {format_currency(kpi_data.get('total_cost_try', 0))}"
    )
    lines.append(
        f"Gerçekleşmemiş K/Z: {format_currency(kpi_data.get('unrealized_pnl', 0))}"
    )
    lines.append(
        f"Gerçekleşmiş K/Z: {format_currency(kpi_data.get('realized_pnl', 0))}"
    )
    lines.append(
        f"Toplam K/Z: {format_currency(kpi_data.get('total_pnl', 0))} "
        f"({format_percent(kpi_data.get('pnl_pct', 0))})"
    )

    # Varlık sınıfı dağılımı
    type_totals: Dict[str, float] = {}
    for item in portfolio_items:
        type_totals[item["type"]] = (
            type_totals.get(item["type"], 0.0) + item["current_value"]
        )
    total_value = kpi_data.get("total_value_try", 0) or 1
    dist = ", ".join(
        f"{t}: %{(v / total_value * 100):.1f}" for t, v in type_totals.items()
    )
    lines.append(f"Varlık Sınıfı Dağılımı: {dist}")

    lines.append("")
    lines.append("=== POZİSYONLAR ===")
    # En büyük pozisyondan küçüğe sırala
    sorted_items = sorted(
        portfolio_items, key=lambda x: x.get("current_value", 0), reverse=True
    )
    for item in sorted_items:
        pnl = item.get("unrealized_pnl", 0)
        cost = item.get("total_cost", 0) or 1
        pnl_pct = pnl / cost * 100
        lines.append(
            f"- {item['code']} ({item['name']}, {item['type']}): "
            f"{item['quantity']:.4f} adet, "
            f"ort. maliyet {format_currency(item['avg_cost'])}, "
            f"güncel fiyat {format_currency(item['current_price'])}, "
            f"değer {format_currency(item['current_value'])} "
            f"(portföyün %{item.get('portfolio_pct', 0):.1f}'i), "
            f"K/Z {format_currency(pnl)} ({format_percent(pnl_pct)})"
        )

    return "\n".join(lines)


SYSTEM_PROMPT = (
    "Sen bir kişisel yatırım portföyü takip uygulamasının Türkçe yapay zeka "
    "asistanısın. Kullanıcının BIST hisseleri ve TEFAS fonlarından oluşan "
    "portföyü hakkında soruları yanıtlarsın. Sana verilen portföy verisini "
    "kullanarak net, kısa ve anlaşılır Türkçe cevaplar ver. Sayıları Türk Lirası "
    "(₺) ve yüzde olarak ifade et. Emin olmadığın konularda tahmin yürütme; "
    "verilen veriye dayan. Cevaplarını sade ve doğrudan tut."
)
