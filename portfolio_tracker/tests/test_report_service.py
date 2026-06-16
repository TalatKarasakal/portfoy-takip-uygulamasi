import datetime
from decimal import Decimal

from app.models.transaction import Transaction, TransactionType
from app.services.report_service import compute_monthly_cashflow


def _tx(ttype, qty, price, date_str, commission=0, tax=0):
    return Transaction(
        asset_id=1,
        transaction_type=ttype,
        date=datetime.datetime.strptime(date_str, "%Y-%m-%d").date(),
        quantity=Decimal(str(qty)),
        unit_price=Decimal(str(price)),
        commission=Decimal(str(commission)),
        tax=Decimal(str(tax)),
    )


def test_monthly_cashflow_groups_and_nets():
    txs = [
        _tx(TransactionType.BUY, 10, 100, "2024-01-05", commission=5),    # alım: 1005 çıkış
        _tx(TransactionType.SELL, 4, 150, "2024-01-20", commission=2),    # satım: 598 giriş
        _tx(TransactionType.DIVIDEND, 10, 3, "2024-02-10", tax=4.5),      # temettü: 25.5 giriş
        _tx(TransactionType.SPLIT, 0, 2.0, "2024-02-15"),                 # nakit yok -> atlanır
    ]
    rows = compute_monthly_cashflow(txs)

    assert [r["month"] for r in rows] == ["2024-01", "2024-02"]

    jan = rows[0]
    assert abs(jan["buys"] - 1005.0) < 1e-6
    assert abs(jan["sells"] - 598.0) < 1e-6
    assert abs(jan["fees"] - 7.0) < 1e-6
    assert abs(jan["net"] - (598.0 - 1005.0)) < 1e-6

    feb = rows[1]
    assert abs(feb["dividends"] - 25.5) < 1e-6   # 30 - 4.5
    assert abs(feb["buys"]) < 1e-6
    assert abs(feb["net"] - 25.5) < 1e-6


def test_monthly_cashflow_empty():
    assert compute_monthly_cashflow([]) == []
