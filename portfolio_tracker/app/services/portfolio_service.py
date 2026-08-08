from __future__ import annotations

import datetime
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation, localcontext
from enum import StrEnum
from typing import Any

from app.models.transaction import Transaction, TransactionType

TRADING_DAYS_PER_YEAR = 252
ZERO = Decimal("0")


class PortfolioCalculationError(ValueError):
    pass


class XirrStatus(StrEnum):
    SUCCESS = "başarılı"
    UNAVAILABLE = "hesaplanamadı"
    AMBIGUOUS = "belirsiz"


@dataclass(frozen=True)
class XirrResult:
    status: XirrStatus
    rate: float | None
    message: str = ""
    roots: tuple[float, ...] = ()


@dataclass(frozen=True)
class OpenLot:
    buy_transaction_id: int | None
    acquired_date: datetime.date
    quantity: Decimal
    unit_cost: Decimal


@dataclass(frozen=True)
class LotMatch:
    sale_transaction_id: int | None
    buy_transaction_id: int | None
    quantity: Decimal
    unit_cost: Decimal
    sale_unit_price: Decimal
    cost_basis: Decimal
    net_proceeds: Decimal
    realized_pnl: Decimal
    method: str


@dataclass(frozen=True)
class PortfolioMetrics:
    remaining_quantity: Decimal
    average_cost: Decimal
    realized_pnl: Decimal
    unrealized_pnl: Decimal
    total_cost: Decimal
    open_lots: tuple[OpenLot, ...]
    lot_matches: tuple[LotMatch, ...]
    method: str

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)


def _decimal(value: Any) -> Decimal:
    try:
        return Decimal(str(value or 0))
    except (InvalidOperation, ValueError) as exc:
        raise PortfolioCalculationError(f"Geçersiz sayısal değer: {value}") from exc


class PortfolioService:
    @staticmethod
    def _sorted_transactions(transactions: list[Transaction]) -> list[Transaction]:
        return [
            transaction
            for index, transaction in sorted(
                enumerate(transactions),
                key=lambda item: (
                    item[1].date,
                    item[1].id if item[1].id is not None else 2**63 + item[0],
                ),
            )
        ]

    @staticmethod
    def calculate_cost_and_pnl(
        transactions: list[Transaction],
        current_price: Decimal | float | int,
        method: str = "WAC",
    ) -> PortfolioMetrics:
        """WAC/FIFO/LIFO sonuçlarını, açık lotları ve satış eşleşmelerini döndürür."""
        method = method.upper()
        if method not in {"WAC", "FIFO", "LIFO"}:
            raise ValueError(f"Bilinmeyen maliyet metodu: {method}")
        if not transactions:
            return PortfolioMetrics(ZERO, ZERO, ZERO, ZERO, ZERO, (), (), method)

        txs = PortfolioService._sorted_transactions(transactions)
        market_price = _decimal(current_price)
        realized = ZERO
        matches: list[LotMatch] = []

        if method == "WAC":
            pool_quantity = ZERO
            pool_cost = ZERO
            first_date = txs[0].date
            for tx in txs:
                quantity = _decimal(tx.quantity)
                unit_price = _decimal(tx.unit_price)
                fees = _decimal(tx.commission) + _decimal(tx.tax)
                if tx.transaction_type == TransactionType.BUY:
                    if quantity <= 0:
                        raise PortfolioCalculationError("Alım miktarı sıfırdan büyük olmalıdır.")
                    if pool_quantity == 0:
                        first_date = tx.date
                    pool_quantity += quantity
                    pool_cost += quantity * unit_price + fees
                elif tx.transaction_type == TransactionType.SELL:
                    if quantity > pool_quantity:
                        raise PortfolioCalculationError("Satış miktarı portföy bakiyesini aşıyor.")
                    average = pool_cost / pool_quantity if pool_quantity else ZERO
                    cost_basis = average * quantity
                    net_proceeds = quantity * unit_price - fees
                    pnl = net_proceeds - cost_basis
                    matches.append(
                        LotMatch(
                            tx.id,
                            None,
                            quantity,
                            average,
                            unit_price,
                            cost_basis,
                            net_proceeds,
                            pnl,
                            method,
                        )
                    )
                    realized += pnl
                    pool_quantity -= quantity
                    pool_cost -= cost_basis
                    if pool_quantity == 0:
                        pool_cost = ZERO
                elif tx.transaction_type == TransactionType.DIVIDEND:
                    realized += quantity * unit_price - fees
                elif tx.transaction_type == TransactionType.SPLIT:
                    if unit_price <= 0:
                        raise PortfolioCalculationError("Split oranı sıfırdan büyük olmalıdır.")
                    pool_quantity *= unit_price

            average_cost = pool_cost / pool_quantity if pool_quantity else ZERO
            open_lots = (
                (OpenLot(None, first_date, pool_quantity, average_cost),)
                if pool_quantity > 0
                else ()
            )
            remaining_quantity = pool_quantity
            total_cost = pool_cost
        else:
            inventory: list[dict[str, Any]] = []
            remaining_quantity = ZERO
            for tx in txs:
                quantity = _decimal(tx.quantity)
                unit_price = _decimal(tx.unit_price)
                fees = _decimal(tx.commission) + _decimal(tx.tax)
                if tx.transaction_type == TransactionType.BUY:
                    if quantity <= 0:
                        raise PortfolioCalculationError("Alım miktarı sıfırdan büyük olmalıdır.")
                    inventory.append(
                        {
                            "buy_id": tx.id,
                            "date": tx.date,
                            "quantity": quantity,
                            "unit_cost": (quantity * unit_price + fees) / quantity,
                        }
                    )
                    remaining_quantity += quantity
                elif tx.transaction_type == TransactionType.SELL:
                    if quantity > remaining_quantity:
                        raise PortfolioCalculationError("Satış miktarı portföy bakiyesini aşıyor.")
                    quantity_left = quantity
                    net_total = quantity * unit_price - fees
                    while quantity_left > 0:
                        index = 0 if method == "FIFO" else -1
                        lot = inventory[index]
                        matched_quantity = min(quantity_left, lot["quantity"])
                        cost_basis = matched_quantity * lot["unit_cost"]
                        net_proceeds = net_total * matched_quantity / quantity
                        pnl = net_proceeds - cost_basis
                        matches.append(
                            LotMatch(
                                tx.id,
                                lot["buy_id"],
                                matched_quantity,
                                lot["unit_cost"],
                                unit_price,
                                cost_basis,
                                net_proceeds,
                                pnl,
                                method,
                            )
                        )
                        realized += pnl
                        lot["quantity"] -= matched_quantity
                        quantity_left -= matched_quantity
                        if lot["quantity"] == 0:
                            inventory.pop(index)
                    remaining_quantity -= quantity
                elif tx.transaction_type == TransactionType.DIVIDEND:
                    realized += quantity * unit_price - fees
                elif tx.transaction_type == TransactionType.SPLIT:
                    if unit_price <= 0:
                        raise PortfolioCalculationError("Split oranı sıfırdan büyük olmalıdır.")
                    for lot in inventory:
                        lot["quantity"] *= unit_price
                        lot["unit_cost"] /= unit_price
                    remaining_quantity *= unit_price

            total_cost = sum(
                (lot["quantity"] * lot["unit_cost"] for lot in inventory),
                ZERO,
            )
            average_cost = total_cost / remaining_quantity if remaining_quantity else ZERO
            open_lots = tuple(
                OpenLot(lot["buy_id"], lot["date"], lot["quantity"], lot["unit_cost"])
                for lot in inventory
            )

        unrealized = (
            (market_price - average_cost) * remaining_quantity
            if remaining_quantity > 0 and market_price > 0
            else ZERO
        )
        return PortfolioMetrics(
            remaining_quantity,
            average_cost,
            realized,
            unrealized,
            total_cost,
            open_lots,
            tuple(matches),
            method,
        )

    @staticmethod
    def calculate_risk_metrics(values: list[float]) -> dict[str, float]:
        empty = {"sharpe": 0.0, "volatility": 0.0, "max_drawdown": 0.0}
        if len(values) < 2:
            return empty
        returns = [cur / prev - 1.0 for prev, cur in zip(values[:-1], values[1:]) if prev > 0]
        if len(returns) < 2:
            return empty
        mean_return = sum(returns) / len(returns)
        variance = sum((value - mean_return) ** 2 for value in returns) / (len(returns) - 1)
        standard_deviation = math.sqrt(variance)
        volatility = standard_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)
        sharpe = (
            mean_return / standard_deviation * math.sqrt(TRADING_DAYS_PER_YEAR)
            if standard_deviation > 0
            else 0.0
        )
        peak = values[0]
        max_drawdown = 0.0
        for value in values:
            peak = max(peak, value)
            if peak > 0:
                max_drawdown = min(max_drawdown, (value - peak) / peak)
        return {
            "sharpe": sharpe,
            "volatility": volatility,
            "max_drawdown": max_drawdown,
        }

    @staticmethod
    def calculate_twr(history: list[dict[str, Any]]) -> float | None:
        """Sürüm 2 snapshot'larını dış akıştan arındırıp günlük zincirler."""
        reliable = sorted(
            (row for row in history if row.get("calculation_version", 1) >= 2),
            key=lambda row: row["date"],
        )
        if len(reliable) < 2:
            return None
        chain = Decimal("1")
        periods = 0
        for previous, current in zip(reliable[:-1], reliable[1:]):
            previous_value = _decimal(previous["total_value_try"])
            if previous_value <= 0:
                continue
            current_value = _decimal(current["total_value_try"])
            external_flow = _decimal(current.get("net_external_flow_try", 0))
            period_return = (current_value - external_flow) / previous_value - Decimal("1")
            chain *= Decimal("1") + period_return
            periods += 1
        return float(chain - Decimal("1")) if periods else None

    @staticmethod
    def monthly_returns(history: list[dict[str, Any]]) -> dict[tuple[int, int], float]:
        month_end: dict[tuple[int, int], dict[str, Any]] = {}
        for row in history:
            date = row["date"]
            month_end[(date.year, date.month)] = row
        returns: dict[tuple[int, int], float] = {}
        for (year, month), current in month_end.items():
            previous_month = (year - 1, 12) if month == 1 else (year, month - 1)
            previous = month_end.get(previous_month)
            if not previous:
                continue
            period_history = [previous, current]
            twr = PortfolioService.calculate_twr(period_history)
            if twr is not None:
                returns[(year, month)] = twr * 100
        return returns

    @staticmethod
    def calculate_xirr(
        cash_flows: list[tuple[datetime.date, Decimal | float | int]],
    ) -> XirrResult:
        """İşaret kontrollü aralıklı kök taramasıyla güvenli XIRR hesaplar."""
        if len(cash_flows) < 2:
            return XirrResult(XirrStatus.UNAVAILABLE, None, "En az iki nakit akışı gerekir.")
        flows = sorted((date, _decimal(amount)) for date, amount in cash_flows)
        if not any(amount < 0 for _date, amount in flows) or not any(
            amount > 0 for _date, amount in flows
        ):
            return XirrResult(
                XirrStatus.UNAVAILABLE,
                None,
                "XIRR için en az bir negatif ve bir pozitif nakit akışı gerekir.",
            )
        first_date = flows[0][0]

        def xnpv(rate: Decimal) -> Decimal | None:
            if rate <= Decimal("-1"):
                return None
            try:
                with localcontext() as context:
                    context.prec = 40
                    total = ZERO
                    base = Decimal("1") + rate
                    for date, amount in flows:
                        exponent = Decimal((date - first_date).days) / Decimal("365")
                        total += amount / (base**exponent)
                    return total if total.is_finite() else None
            except (InvalidOperation, OverflowError, ValueError):
                return None

        grid = [
            Decimal("-0.9999"), Decimal("-0.99"), Decimal("-0.9"),
            Decimal("-0.75"), Decimal("-0.5"), Decimal("-0.25"), ZERO,
            Decimal("0.01"), Decimal("0.05"), Decimal("0.1"), Decimal("0.2"),
            Decimal("0.5"), Decimal("1"), Decimal("2"), Decimal("5"),
            Decimal("10"), Decimal("100"), Decimal("1000"), Decimal("1000000"),
        ]
        roots: list[Decimal] = []
        for left, right in zip(grid[:-1], grid[1:]):
            left_value = xnpv(left)
            right_value = xnpv(right)
            if left_value is None or right_value is None:
                continue
            if abs(left_value) < Decimal("1e-18"):
                roots.append(left)
                continue
            if left_value * right_value > 0:
                continue
            low, high = left, right
            low_value = left_value
            for _ in range(200):
                middle = (low + high) / 2
                middle_value = xnpv(middle)
                if middle_value is None:
                    break
                if abs(middle_value) < Decimal("1e-18") or high - low < Decimal("1e-16"):
                    roots.append(middle)
                    break
                if low_value * middle_value <= 0:
                    high = middle
                else:
                    low, low_value = middle, middle_value

        unique_roots: list[float] = []
        for root in roots:
            numeric = float(root)
            if math.isfinite(numeric) and not any(abs(numeric - item) < 1e-8 for item in unique_roots):
                unique_roots.append(numeric)
        if not unique_roots:
            return XirrResult(XirrStatus.UNAVAILABLE, None, "Sonlu bir XIRR kökü bulunamadı.")
        if len(unique_roots) > 1:
            return XirrResult(
                XirrStatus.AMBIGUOUS,
                None,
                "Birden fazla olası XIRR kökü bulundu.",
                tuple(unique_roots),
            )
        return XirrResult(XirrStatus.SUCCESS, unique_roots[0], roots=tuple(unique_roots))
