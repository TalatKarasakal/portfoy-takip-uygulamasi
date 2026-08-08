import datetime
import math
from decimal import Decimal

import pytest

from app.models.transaction import Transaction, TransactionType
from app.services.portfolio_service import PortfolioService, XirrStatus


class MockAsset:
    def __init__(self, id):
        self.id = id

def build_tx(tx_type, qty, price, date_str, commission=0, tax=0):
    tx = Transaction(
        asset_id=1,
        transaction_type=tx_type,
        date=datetime.datetime.strptime(date_str, "%Y-%m-%d").date(),
        quantity=Decimal(str(qty)),
        unit_price=Decimal(str(price)),
        commission=Decimal(str(commission)),
        tax=Decimal(str(tax))
    )
    return tx

@pytest.fixture
def transactions():
    return [
        build_tx(TransactionType.BUY, 10, 100, "2023-01-01"),
        build_tx(TransactionType.BUY, 20, 130, "2023-02-01"),
        build_tx(TransactionType.SELL, 15, 150, "2023-03-01")
    ]

def test_wac_method(transactions):
    res = PortfolioService.calculate_cost_and_pnl(transactions, current_price=160, method="WAC")

    assert res["remaining_quantity"] == 15
    # Toplam Alım: 10*100 + 20*130 = 1000 + 2600 = 3600
    # WAC birim maliyeti satış anında: 3600 / 30 = 120
    # 15 adet satılınca maliyeti 15 * 120 = 1800 oluyor. Sell işlemindeki gelir: 15 * 150 = 2250
    # Realized PNL = 2250 - 1800 = 450
    # Kalan envanter için Average Cost 120
    # Kalan değer: 15 adet. Unrealized PNL = (160 - 120) * 15 = 600

    assert abs(res["average_cost"] - 120) < 1e-4
    assert abs(res["realized_pnl"] - 450) < 1e-4
    assert abs(res["unrealized_pnl"] - 600) < 1e-4

def test_fifo_method(transactions):
    res = PortfolioService.calculate_cost_and_pnl(transactions, current_price=160, method="FIFO")
    assert res["remaining_quantity"] == 15

    # 15 satılıyor. İlk giren 10 adet (maliyet 100). Sonraki giren 20'nin 5'i gider (maliyet 130).
    # Satılan maliyet: (10 * 100) + (5 * 130) = 1000 + 650 = 1650
    # Satış geliri: 15 * 150 = 2250
    # Realized PNL = 2250 - 1650 = 600
    assert abs(res["realized_pnl"] - 600) < 1e-4

    # Kalan envanter: 15 adet maliyetli 130. Ortalama maliyet 130.
    assert abs(res["average_cost"] - 130) < 1e-4

    # Unrealized = (160 - 130) * 15 = 450
    assert abs(res["unrealized_pnl"] - 450) < 1e-4

def test_lifo_method(transactions):
    res = PortfolioService.calculate_cost_and_pnl(transactions, current_price=160, method="LIFO")
    assert res["remaining_quantity"] == 15

    # 15 satılıyor. Son giren 20 adet (maliyet 130). Buradan 15'i gider.
    # Satılan Maliyet = 15 * 130 = 1950
    # Satış geliri = 15 * 150 = 2250
    # Realized = 2250 - 1950 = 300
    assert abs(res["realized_pnl"] - 300) < 1e-4

    # Kalan envanter: 10 adet(100) + 5 adet(130)
    # Toplam kalan maliyet = 1000 + 650 = 1650
    # Ortalama = 1650 / 15 = 110
    assert abs(res["average_cost"] - 110) < 1e-4

    # Unrealized = (160 - 110) * 15 = 750
    assert abs(res["unrealized_pnl"] - 750) < 1e-4

def test_xirr_calculation():
    # Gün 0: 1000 lira yatırım (-1000)
    # Gün 365: 1100 lira çekim (+1100)
    # Beklenen getiri ~%10
    t0 = datetime.date(2023, 1, 1)
    t1 = datetime.date(2024, 1, 1)
    cash_flows = [(t0, -1000.0), (t1, 1100.0)]
    result = PortfolioService.calculate_xirr(cash_flows)
    assert result.status == XirrStatus.SUCCESS
    assert result.rate is not None and 0.09 < result.rate < 0.11


def test_full_exit_keeps_realized_pnl():
    # Pozisyondan tamamen çıkıldığında bile gerçekleşmiş K/Z hesaplanmalı.
    # (Loader bu değeri portföyden çıkılan varlıklar için de toplar.)
    txs = [
        build_tx(TransactionType.BUY, 10, 100, "2023-01-01"),
        build_tx(TransactionType.SELL, 10, 120, "2023-02-01"),
    ]
    res = PortfolioService.calculate_cost_and_pnl(txs, current_price=0, method="WAC")
    assert res["remaining_quantity"] == 0
    assert abs(res["realized_pnl"] - 200) < 1e-6  # (120 - 100) * 10
    assert res["unrealized_pnl"] == 0


def test_risk_metrics_insufficient_data():
    empty = {"sharpe": 0.0, "volatility": 0.0, "max_drawdown": 0.0}
    assert PortfolioService.calculate_risk_metrics([]) == empty
    assert PortfolioService.calculate_risk_metrics([100]) == empty


def test_risk_metrics_max_drawdown():
    # 100 -> 50 => -%50 düşüş, sonra kısmi toparlanma
    res = PortfolioService.calculate_risk_metrics([100, 50, 75])
    assert abs(res["max_drawdown"] - (-0.5)) < 1e-9
    assert res["volatility"] >= 0


def test_risk_metrics_no_drawdown_when_monotonic():
    res = PortfolioService.calculate_risk_metrics([100, 101, 102, 103])
    assert res["max_drawdown"] == 0.0
    assert res["sharpe"] > 0  # sürekli artış pozitif Sharpe verir


def test_dividend_adds_to_realized_pnl():
    # 10 hisse al; sonra 10 hisseye hisse başı 2 TL temettü (toplam 20), 3 TL stopaj
    txs = [
        build_tx(TransactionType.BUY, 10, 100, "2023-01-01"),
        build_tx(TransactionType.DIVIDEND, 10, 2, "2023-03-01", tax=3),
    ]
    res = PortfolioService.calculate_cost_and_pnl(txs, current_price=110, method="WAC")
    # Temettü adedi/maliyeti değiştirmez
    assert res["remaining_quantity"] == 10
    assert abs(res["average_cost"] - 100) < 1e-6
    # net temettü = 20 - 3 = 17
    assert abs(res["realized_pnl"] - 17) < 1e-6
    assert abs(res["unrealized_pnl"] - 100) < 1e-6  # (110-100)*10


def test_split_doubles_quantity_halves_cost_wac():
    # 10 hisse @100 (toplam maliyet 1000), 1:1 bedelsiz => katsayı 2.0
    txs = [
        build_tx(TransactionType.BUY, 10, 100, "2023-01-01"),
        build_tx(TransactionType.SPLIT, 0, 2.0, "2023-02-01"),
    ]
    res = PortfolioService.calculate_cost_and_pnl(txs, current_price=60, method="WAC")
    assert abs(res["remaining_quantity"] - 20) < 1e-6
    assert abs(res["average_cost"] - 50) < 1e-6        # 1000/20
    assert abs(res["total_cost"] - 1000) < 1e-6        # toplam maliyet sabit
    assert abs(res["unrealized_pnl"] - 200) < 1e-6     # (60-50)*20


def test_split_fifo():
    txs = [
        build_tx(TransactionType.BUY, 10, 100, "2023-01-01"),
        build_tx(TransactionType.SPLIT, 0, 2.0, "2023-02-01"),
    ]
    res = PortfolioService.calculate_cost_and_pnl(txs, current_price=60, method="FIFO")
    assert abs(res["remaining_quantity"] - 20) < 1e-6
    assert abs(res["average_cost"] - 50) < 1e-6
    assert abs(res["unrealized_pnl"] - 200) < 1e-6


def test_monthly_returns():
    history = [
        {"date": datetime.date(2024, 1, 31), "total_value_try": 1000.0, "calculation_version": 2},
        {"date": datetime.date(2024, 2, 29), "total_value_try": 1100.0, "calculation_version": 2},
        {"date": datetime.date(2024, 3, 31), "total_value_try": 990.0, "calculation_version": 2},
        {"date": datetime.date(2024, 5, 31), "total_value_try": 1200.0, "calculation_version": 2},
    ]
    r = PortfolioService.monthly_returns(history)
    assert abs(r[(2024, 2)] - 10.0) < 1e-6
    assert abs(r[(2024, 3)] - (-10.0)) < 1e-6
    # Mayıs'ın bir önceki takvim ayı (Nisan) yok -> getiri hesaplanmaz
    assert (2024, 5) not in r
    # Ocak'ın öncesi yok
    assert (2024, 1) not in r


def test_xirr_requires_both_cash_flow_signs():
    result = PortfolioService.calculate_xirr(
        [
            (datetime.date(2024, 1, 1), 100),
            (datetime.date(2025, 1, 1), 110),
        ]
    )
    assert result.status == XirrStatus.UNAVAILABLE
    assert result.rate is None


def test_xirr_reports_multiple_roots_as_ambiguous():
    result = PortfolioService.calculate_xirr(
        [
            (datetime.date(2022, 1, 1), -100),
            (datetime.date(2023, 1, 1), 230),
            (datetime.date(2024, 1, 1), -132),
        ]
    )
    assert result.status == XirrStatus.AMBIGUOUS
    assert result.rate is None
    assert len(result.roots) >= 2


def test_xirr_extreme_root_never_reaches_ui_as_non_finite():
    result = PortfolioService.calculate_xirr(
        [
            (datetime.date(2024, 1, 1), -1),
            (datetime.date(2025, 1, 1), Decimal("1e100")),
        ]
    )
    assert result.status == XirrStatus.UNAVAILABLE
    assert result.rate is None
    assert all(math.isfinite(root) for root in result.roots)


def test_twr_is_neutral_to_external_deposit():
    history = [
        {
            "date": datetime.date(2024, 1, 1),
            "total_value_try": 1000,
            "net_external_flow_try": 0,
            "calculation_version": 2,
        },
        {
            "date": datetime.date(2024, 1, 2),
            "total_value_try": 1500,
            "net_external_flow_try": 500,
            "calculation_version": 2,
        },
    ]
    assert PortfolioService.calculate_twr(history) == 0.0


def test_twr_does_not_claim_reliability_for_legacy_snapshots():
    history = [
        {"date": datetime.date(2024, 1, 1), "total_value_try": 1000},
        {"date": datetime.date(2024, 1, 2), "total_value_try": 1200},
    ]
    assert PortfolioService.calculate_twr(history) is None


def test_fifo_returns_open_lots_and_sale_matches(transactions):
    for tx_id, transaction in enumerate(transactions, start=1):
        transaction.id = tx_id
    result = PortfolioService.calculate_cost_and_pnl(
        transactions, current_price=160, method="FIFO"
    )
    assert len(result.lot_matches) == 2
    assert [match.buy_transaction_id for match in result.lot_matches] == [1, 2]
    assert result.lot_matches[0].sale_transaction_id == 3
    assert len(result.open_lots) == 1
    assert result.open_lots[0].quantity == Decimal("15")
