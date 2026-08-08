import datetime

from PySide6.QtCore import QObject, Signal

from app.database.session import get_session
from app.models.transaction import Transaction, TransactionType
from app.services.benchmark_service import BenchmarkService
from app.services.portfolio_service import PortfolioService
from app.services.snapshot_service import SnapshotService
from app.utils.logger import app_logger
from app.viewmodels.worker import FunctionWorker, stop_worker


class AnalyticsViewModel(QObject):
    analytics_loaded = Signal(dict)
    benchmark_loaded = Signal(dict)
    error_occurred = Signal(str)

    def __init__(self) -> None:
        super().__init__()
        self._benchmark_worker: FunctionWorker | None = None

    def load_analytics_data(self, portfolio_items: list):
        """portfolio_items: PortfolioViewModel'dan hesaplanmış güncel liste"""
        try:
            with get_session() as session:
                txs = session.query(Transaction).all()

                # 1. XIRR Hesabı: Tüm nakit akışlarını çıkar
                cash_flows = []
                for tx in txs:
                    # Alım negatif nakit çıkışı, satış/temettü pozitif nakit girişi.
                    # SPLIT nakit akışı üretmez (unit_price = katsayı, tutar değil).
                    if tx.transaction_type == TransactionType.SPLIT:
                        continue
                    if tx.transaction_type == TransactionType.BUY:
                        cash_flows.append((tx.date, -float(tx.total_cost)))
                    else:
                        # net satış/temettü geliri
                        net_revenue = (float(tx.unit_price) * float(tx.quantity)) - float(tx.commission) - float(tx.tax)
                        cash_flows.append((tx.date, net_revenue))

                # Güncel portföy değerini pozitif nakit akışı (+ bugünkü değer) olarak ekle
                total_current_value = sum(item["current_value"] for item in portfolio_items)
                if total_current_value > 0 and cash_flows:
                    cash_flows.append((datetime.date.today(), total_current_value))

                xirr_val = PortfolioService.calculate_xirr(cash_flows)

                # 2. Varlık Sınıfı Dağılımı
                alloc_type = {"BIST": 0, "TEFAS": 0}
                for item in portfolio_items:
                    alloc_type[item["type"]] += item["current_value"]

                # 3. Bireysel Varlık Dağılımı
                alloc_asset = [{"name": item["code"], "value": item["current_value"]} for item in portfolio_items if item["current_value"] > 0]
                alloc_asset.sort(key=lambda x: x["value"], reverse=True)

                # 3b. Varlık K/Z katkısı (attribution) — TL bazında
                attribution = [
                    {"code": item["code"],
                     "pnl": item.get("realized_pnl", 0) + item.get("unrealized_pnl", 0)}
                    for item in portfolio_items
                ]
                attribution.sort(key=lambda x: x["pnl"], reverse=True)

                # 4. Performans zaman serisi (gerçek snapshot geçmişi)
                history = SnapshotService.get_history(session)

                # 5. Risk metrikleri (günlük getirilerden)
                metrics = PortfolioService.calculate_risk_metrics(
                    [h["total_value_try"] for h in history]
                )

                self.analytics_loaded.emit({
                    "xirr": xirr_val,
                    "allocation_type": alloc_type,
                    "allocation_asset": alloc_asset,
                    "attribution": attribution,
                    "history": history,
                    "sharpe": metrics["sharpe"],
                    "volatility": metrics["volatility"],
                    "max_drawdown": metrics["max_drawdown"],
                    "monthly_returns": PortfolioService.monthly_returns(history),
                })
        except Exception as e:
            app_logger.error(f"Analytics load error: {e}")
            self.error_occurred.emit(str(e))

    def load_benchmark(self, start: datetime.date, end: datetime.date) -> None:
        if self._benchmark_worker is not None and self._benchmark_worker.isRunning():
            return
        request = (start, end)
        worker = FunctionWorker(
            "benchmark",
            lambda: BenchmarkService.fetch_series(request[0], request[1]),
        )
        worker.result_ready.connect(lambda _tag, result: self.benchmark_loaded.emit(result or {}))
        worker.error_occurred.connect(lambda _tag, message: self.error_occurred.emit(message))
        worker.finished.connect(self._clear_benchmark_worker)
        self._benchmark_worker = worker
        worker.start()

    def _clear_benchmark_worker(self) -> None:
        self._benchmark_worker = None

    def shutdown(self) -> None:
        stop_worker(self._benchmark_worker)
        self._benchmark_worker = None
