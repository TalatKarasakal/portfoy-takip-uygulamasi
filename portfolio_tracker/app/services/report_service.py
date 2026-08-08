"""Aylık nakit akışı raporu.

İşlem geçmişinden (alım/satım/temettü) aylık nakit giriş-çıkış özetini
hesaplar ve Excel'e aktarır. Hesaplama tamamen deterministiktir (LLM/ağ
gerektirmez) ve birim testlerle doğrulanabilir.
"""

from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal
from enum import StrEnum
from html import escape
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd
from PySide6.QtCore import QRectF, QUrl
from PySide6.QtGui import QColor, QImage, QPageSize, QPainter, QPdfWriter, QPen, QTextDocument
from sqlalchemy.orm import Session

from app.models.dividend_plan import DividendPlan
from app.models.portfolio import CashEntry
from app.models.transaction import Transaction, TransactionType
from app.utils.logger import app_logger


class ReportMode(StrEnum):
    SUMMARY = "summary"
    AUDIT = "audit"


@dataclass(frozen=True)
class PdfReportResult:
    success: bool
    path: Path
    mode: ReportMode
    error: str = ""

    def __bool__(self) -> bool:
        return self.success


def _performance_chart(history: list[dict[str, Any]]) -> QImage:
    image = QImage(900, 280, QImage.Format_ARGB32)
    image.fill(QColor("#FFFFFF"))
    painter = QPainter(image)
    painter.setRenderHint(QPainter.Antialiasing)
    painter.setPen(QPen(QColor("#D1D5DB"), 1))
    painter.drawRect(QRectF(45, 20, 830, 220))
    values = [float(row.get("total_value_try", 0)) for row in history]
    if len(values) >= 2 and max(values) > min(values):
        low, high = min(values), max(values)
        points = []
        for index, value in enumerate(values):
            x = 45 + index / (len(values) - 1) * 830
            y = 240 - (value - low) / (high - low) * 220
            points.append((x, y))
        painter.setPen(QPen(QColor("#00B5E2"), 3))
        for previous, current in zip(points[:-1], points[1:]):
            painter.drawLine(previous[0], previous[1], current[0], current[1])
    painter.end()
    return image


def _html_table(headers: list[str], rows: list[list[Any]]) -> str:
    head = "".join(f"<th>{escape(header)}</th>" for header in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{escape(str(value))}</td>" for value in row) + "</tr>"
        for row in rows
    )
    return f"<table><thead><tr>{head}</tr></thead><tbody>{body}</tbody></table>"


def export_portfolio_pdf(
    session: Session,
    file_path: str,
    mode: ReportMode | str,
    portfolio_id: int | None,
    kpi: dict[str, Any],
) -> PdfReportResult:
    """Özet veya tam denetim PDF'ini yerel verilerden üretir."""
    selected_mode = mode if isinstance(mode, ReportMode) else ReportMode(mode)
    path = Path(file_path)
    try:
        items = kpi.get("portfolio_items", [])
        history = kpi.get("history", [])
        style = """
        <style>
        body { font-family: Inter, sans-serif; color: #111827; }
        h1, h2 { color: #0F4C5C; }
        table { width: 100%; border-collapse: collapse; margin-bottom: 16px; }
        th, td { border: 1px solid #D1D5DB; padding: 5px; font-size: 9pt; }
        th { background: #E5F6FA; }
        .metrics { font-size: 12pt; }
        </style>
        """
        sections = [
            "<h1>Portföy Takip ve Analiz Raporu</h1>",
            f"<p>Rapor türü: {'Tam Denetim' if selected_mode == ReportMode.AUDIT else 'Özet'}</p>",
            "<h2>Özet ve Performans</h2>",
            (
                f"<p class='metrics'>Toplam Değer: {kpi.get('total_value_try', 0):,.2f} TL<br>"
                f"Nakit: {kpi.get('cash_balance_try', 0):,.2f} TL<br>"
                f"Gerçekleşmiş K/Z: {kpi.get('realized_pnl', 0):,.2f} TL<br>"
                f"Gerçekleşmemiş K/Z: {kpi.get('unrealized_pnl', 0):,.2f} TL</p>"
            ),
            '<img src="chart.png" width="700" height="218">',
            "<h2>Varlıklar</h2>",
            _html_table(
                ["Kod", "Adet", "Maliyet", "Fiyat", "Değer", "Durum"],
                [
                    [
                        item.get("code"), item.get("quantity"), item.get("avg_cost"),
                        item.get("current_price"), item.get("current_value"),
                        item.get("price_status"),
                    ]
                    for item in items
                ],
            ),
        ]
        if selected_mode == ReportMode.AUDIT:
            transaction_query = session.query(Transaction)
            cash_query = session.query(CashEntry)
            plan_query = session.query(DividendPlan)
            if portfolio_id is not None:
                transaction_query = transaction_query.filter(
                    Transaction.portfolio_id == portfolio_id
                )
                cash_query = cash_query.filter(CashEntry.portfolio_id == portfolio_id)
                plan_query = plan_query.filter(DividendPlan.portfolio_id == portfolio_id)
            transactions = transaction_query.order_by(Transaction.date, Transaction.id).all()
            cash_entries = cash_query.order_by(CashEntry.date, CashEntry.id).all()
            plans = plan_query.order_by(DividendPlan.payment_date, DividendPlan.id).all()
            lot_rows = []
            for asset in kpi.get("lot_analysis", []):
                for match in asset.get("lot_matches", []):
                    lot_rows.append(
                        [
                            asset["code"], match["method"], match["buy_transaction_id"],
                            match["sale_transaction_id"], match["quantity"],
                            match["realized_pnl"],
                        ]
                    )
            sections.extend(
                [
                    "<h2>İşlemler</h2>",
                    _html_table(
                        ["Tarih", "Tür", "Varlık ID", "Adet", "Fiyat", "Masraf"],
                        [
                            [
                                row.date, row.transaction_type.name, row.asset_id,
                                row.quantity, row.unit_price,
                                row.commission + row.tax,
                            ]
                            for row in transactions
                        ],
                    ),
                    "<h2>Nakit Defteri</h2>",
                    _html_table(
                        ["Tarih", "Tür", "Tutar", "Not"],
                        [[row.date, row.entry_type.name, row.amount, row.note or ""] for row in cash_entries],
                    ),
                    "<h2>Temettü Planları</h2>",
                    _html_table(
                        ["Tarih", "Varlık ID", "Hisse Başı", "Adet", "Durum"],
                        [
                            [
                                row.payment_date, row.asset_id, row.gross_per_share,
                                row.expected_quantity or "—", row.status.name,
                            ]
                            for row in plans
                        ],
                    ),
                    "<h2>Lot Eşleşmeleri</h2>",
                    _html_table(
                        ["Kod", "Yöntem", "Alım ID", "Satış ID", "Adet", "K/Z"],
                        lot_rows,
                    ),
                    "<h2>Veri Kaynağı ve Tazelik</h2>",
                    _html_table(
                        ["Kod", "Kaynak", "Fiyat Tarihi", "Çekilme", "Durum"],
                        [
                            [
                                item.get("code"), item.get("price_source"),
                                item.get("price_date"), item.get("price_fetched_at"),
                                item.get("price_status"),
                            ]
                            for item in items
                        ],
                    ),
                ]
            )
        writer = QPdfWriter(str(path))
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setResolution(120)
        document = QTextDocument()
        document.addResource(QTextDocument.ImageResource, QUrl("chart.png"), _performance_chart(history))
        document.setHtml(style + "".join(sections))
        document.print_(writer)
        return PdfReportResult(True, path, selected_mode)
    except Exception as exc:
        app_logger.error("PDF raporu üretilemedi: %s", exc)
        return PdfReportResult(False, path, selected_mode, str(exc))


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
    months: Dict[str, Dict[str, Decimal]] = defaultdict(
        lambda: {
            "buys": Decimal("0"),
            "sells": Decimal("0"),
            "dividends": Decimal("0"),
            "fees": Decimal("0"),
        }
    )

    for tx in transactions:
        key = tx.date.strftime("%Y-%m")
        qty = Decimal(str(tx.quantity))
        price = Decimal(str(tx.unit_price))
        fees = Decimal(str(tx.commission)) + Decimal(str(tx.tax))
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
            "buys": float(m["buys"]),
            "sells": float(m["sells"]),
            "dividends": float(m["dividends"]),
            "fees": float(m["fees"]),
            "net": float(m["sells"] + m["dividends"] - m["buys"]),
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
