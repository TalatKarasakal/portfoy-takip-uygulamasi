import datetime
from decimal import Decimal

from PySide6.QtCore import QObject, Signal

from app.database.session import get_session
from app.models.portfolio import CashEntry
from app.services.benchmark_service import BenchmarkService
from app.services.dividend_service import DividendService
from app.services.portfolio_account_service import PortfolioAccountService
from app.services.portfolio_service import PortfolioService
from app.services.snapshot_service import SnapshotService
from app.utils.logger import app_logger
from app.viewmodels.worker import FunctionWorker, stop_worker


class AnalyticsViewModel(QObject):
    analytics_loaded = Signal(dict)
    benchmark_loaded = Signal(object)
    dividend_action_completed = Signal(str)
    error_occurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._benchmark_worker: FunctionWorker | None = None
        self.selected_portfolio_id: int | None = 1
        self._last_kpi: dict = {}

    def set_portfolio(self, portfolio_id) -> None:
        self.selected_portfolio_id = int(portfolio_id) if portfolio_id is not None else None

    def load_analytics_data(self, source: dict | list):
        """KPI DTO'sundan güvenilir getiri, lot ve temettü analizini üretir."""
        try:
            kpi = source if isinstance(source, dict) else {"portfolio_items": source}
            self._last_kpi = kpi
            portfolio_items = kpi.get("portfolio_items", [])
            total_current_value = float(
                kpi.get(
                    "total_value_try",
                    sum(item.get("current_value", 0) for item in portfolio_items),
                )
            )
            with get_session() as session:
                cash_query = session.query(CashEntry)
                if self.selected_portfolio_id is not None:
                    cash_query = cash_query.filter(
                        CashEntry.portfolio_id == self.selected_portfolio_id
                    )
                cash_flows = [
                    (row.date, -PortfolioAccountService.signed_cash_entry(row))
                    for row in cash_query.all()
                ]
                if total_current_value > 0 and cash_flows:
                    cash_flows.append(
                        (datetime.date.today(), Decimal(str(total_current_value)))
                    )
                xirr_result = PortfolioService.calculate_xirr(cash_flows)

                allocation_type = {"BIST": 0.0, "TEFAS": 0.0}
                for item in portfolio_items:
                    allocation_type[item["type"]] += item["current_value"]
                allocation_asset = [
                    {"name": item["code"], "value": item["current_value"]}
                    for item in portfolio_items
                    if item["current_value"] > 0
                ]
                allocation_asset.sort(key=lambda item: item["value"], reverse=True)
                attribution = [
                    {
                        "code": item["code"],
                        "pnl": item.get("realized_pnl", 0)
                        + item.get("unrealized_pnl", 0),
                    }
                    for item in portfolio_items
                ]
                attribution.sort(key=lambda item: item["pnl"], reverse=True)

                history = (
                    SnapshotService.get_history(
                        session, portfolio_id=self.selected_portfolio_id
                    )
                    if self.selected_portfolio_id is not None
                    else SnapshotService.get_consolidated_history(session)
                )
                risk_metrics = PortfolioService.calculate_risk_metrics(
                    [row["total_value_try"] for row in history]
                )
                twr = PortfolioService.calculate_twr(history)
                dividends = DividendService.dashboard(
                    session, self.selected_portfolio_id, portfolio_items
                )

                total_cost = float(kpi.get("total_cost_try", 0))
                realized = float(kpi.get("realized_pnl", 0))
                unrealized = float(kpi.get("unrealized_pnl", 0))
                self.analytics_loaded.emit(
                    {
                        "xirr_result": xirr_result,
                        "twr": twr,
                        "allocation_type": allocation_type,
                        "allocation_asset": allocation_asset,
                        "attribution": attribution,
                        "history": history,
                        "sharpe": risk_metrics["sharpe"],
                        "volatility": risk_metrics["volatility"],
                        "max_drawdown": risk_metrics["max_drawdown"],
                        "monthly_returns": PortfolioService.monthly_returns(history),
                        "open_position_return": (
                            unrealized / total_cost if total_cost > 0 else None
                        ),
                        "realized_pnl": realized,
                        "unrealized_pnl": unrealized,
                        "total_cost": total_cost,
                        "total_value": total_current_value,
                        "dividends": dividends,
                        "lot_analysis": kpi.get("lot_analysis", []),
                        "asset_choices": [
                            {
                                "id": item["id"],
                                "code": item["code"],
                                "quantity": item["quantity"],
                            }
                            for item in portfolio_items
                        ],
                    }
                )
        except Exception as exc:
            app_logger.error(f"Analytics load error: {exc}")
            self.error_occurred.emit(str(exc))

    def add_dividend_plan(
        self,
        asset_id: int,
        payment_date: datetime.date,
        gross_per_share: float,
        expected_quantity: float | None,
        note: str,
    ) -> None:
        if self.selected_portfolio_id is None:
            self.error_occurred.emit("Temettü planı için belirli bir portföy seçin.")
            return
        try:
            with get_session() as session:
                with session.begin():
                    DividendService.add_plan(
                        session,
                        self.selected_portfolio_id,
                        asset_id,
                        payment_date,
                        gross_per_share,
                        expected_quantity,
                        note,
                    )
            self.dividend_action_completed.emit("Temettü planı eklendi.")
            self.load_analytics_data(self._last_kpi)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def mark_dividend_paid(self, plan_id: int, quantity: float) -> None:
        try:
            with get_session() as session:
                with session.begin():
                    DividendService.mark_paid(session, plan_id, quantity)
            self.dividend_action_completed.emit("Temettü işlemi atomik olarak kaydedildi.")
            self.load_analytics_data(self._last_kpi)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def load_benchmark(self, start: datetime.date, end: datetime.date) -> None:
        if self._benchmark_worker is not None and self._benchmark_worker.isRunning():
            return
        request = (start, end)
        worker = FunctionWorker(
            "benchmark",
            lambda: BenchmarkService.fetch_series(request[0], request[1]),
        )
        worker.result_ready.connect(
            lambda _tag, result: self.benchmark_loaded.emit(result)
        )
        worker.error_occurred.connect(
            lambda _tag, message: self.error_occurred.emit(message)
        )
        worker.finished.connect(self._clear_benchmark_worker)
        self._benchmark_worker = worker
        worker.start()

    def _clear_benchmark_worker(self) -> None:
        self._benchmark_worker = None

    def shutdown(self) -> None:
        stop_worker(self._benchmark_worker)
        self._benchmark_worker = None
