"""Aylık nakit akışı raporu.

İşlem geçmişinden (alım/satım/temettü) aylık nakit giriş-çıkış özetini
hesaplar ve Excel'e aktarır. Hesaplama tamamen deterministiktir (LLM/ağ
gerektirmez) ve birim testlerle doğrulanabilir.
"""

from collections import defaultdict
from typing import Any, Dict, List

import pandas as pd
from sqlalchemy.orm import Session

from app.models.transaction import Transaction, TransactionType
from app.utils.logger import app_logger


def compute_monthly_cashflow(transactions: List[Transaction]) -> List[Dict[str, Any]]:
    """İşlemlerden aylık nakit akışını hesaplar.

    Sözleşme (her satır bir ay):
        * ``buys``: O ay alımlara ödenen toplam (masraflar dahil) — nakit çıkışı.
        * ``sells``: Satışlardan elde edilen net gelir (masraflar düşülmüş).
        * ``dividends``: Net temettü geliri.
        * ``fees``: O ayki toplam komisyon + vergi (bilgi amaçlı).
        * ``net``: ``sells + dividends - buys`` (net nakit akışı).

    SPLIT (bedelsiz/bölünme) işlemleri nakit içermediği için atlanır.

    Returns:
        Aya ("YYYY-MM") göre artan sıralı sözlük listesi.
    """
    months: Dict[str, Dict[str, float]] = defaultdict(
        lambda: {"buys": 0.0, "sells": 0.0, "dividends": 0.0, "fees": 0.0}
    )

    for tx in transactions:
        key = tx.date.strftime("%Y-%m")
        qty = float(tx.quantity)
        price = float(tx.unit_price)
        fees = float(tx.commission) + float(tx.tax)
        gross = qty * price
        ttype = tx.transaction_type

        if ttype == TransactionType.BUY:
            months[key]["buys"] += gross + fees
            months[key]["fees"] += fees
        elif ttype == TransactionType.SELL:
            months[key]["sells"] += gross - fees
            months[key]["fees"] += fees
        elif ttype == TransactionType.DIVIDEND:
            months[key]["dividends"] += gross - fees
            months[key]["fees"] += fees
        # SPLIT: nakit akışı yok -> atla

    result: List[Dict[str, Any]] = []
    for key in sorted(months):
        m = months[key]
        result.append({
            "month": key,
            "buys": m["buys"],
            "sells": m["sells"],
            "dividends": m["dividends"],
            "fees": m["fees"],
            "net": m["sells"] + m["dividends"] - m["buys"],
        })
    return result


def export_cashflow_excel(session: Session, file_path: str) -> bool:
    """Aylık nakit akışı tablosunu Excel'e aktarır.

    Returns:
        En az bir işlem varsa True; hiç işlem yoksa False.
    """
    txs = session.query(Transaction).all()
    rows = compute_monthly_cashflow(txs)
    if not rows:
        return False

    data = [
        {
            "Ay": r["month"],
            "Alımlar (TL)": round(r["buys"], 2),
            "Satımlar (TL)": round(r["sells"], 2),
            "Temettü (TL)": round(r["dividends"], 2),
            "Komisyon+Vergi (TL)": round(r["fees"], 2),
            "Net Nakit Akışı (TL)": round(r["net"], 2),
        }
        for r in rows
    ]
    # Toplam satırı
    data.append({
        "Ay": "TOPLAM",
        "Alımlar (TL)": round(sum(r["buys"] for r in rows), 2),
        "Satımlar (TL)": round(sum(r["sells"] for r in rows), 2),
        "Temettü (TL)": round(sum(r["dividends"] for r in rows), 2),
        "Komisyon+Vergi (TL)": round(sum(r["fees"] for r in rows), 2),
        "Net Nakit Akışı (TL)": round(sum(r["net"] for r in rows), 2),
    })

    with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
        pd.DataFrame(data).to_excel(writer, sheet_name="Aylık Nakit Akışı", index=False)

    app_logger.info(f"Aylık nakit akışı raporu dışa aktarıldı: {file_path}")
    return True
