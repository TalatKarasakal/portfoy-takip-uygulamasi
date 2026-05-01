import math
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy.orm import joinedload
from PySide6.QtCore import QObject, Signal, Slot, QThread
from app.database.session import get_session
from app.models.asset import Asset, AssetType
from app.services.bist_service import BistService
from app.services.tefas_service import TefasService
from app.services.portfolio_service import PortfolioService
from app.utils.logger import app_logger

class PortfolioLoaderThread(QThread):
    data_loaded_signal = Signal(list, dict)
    error_signal = Signal(str)

    def __init__(self, cost_method, force_refresh, bist_service, tefas_service):
        super().__init__()
        self.cost_method = cost_method
        self.force_refresh = force_refresh
        self.bist_service = bist_service
        self.tefas_service = tefas_service

    def run(self):
        try:
            with get_session() as session:
                assets = session.query(Asset).options(joinedload(Asset.transactions)).all()
                portfolio_items = []
                
                total_value_try = 0.0
                total_cost_try = 0.0
                realized_pnl_total = 0.0
                unrealized_pnl_total = 0.0
                
                def fetch_price(asset):
                    if asset.asset_type == AssetType.BIST:
                        return asset, self.bist_service.fetch_current_price(asset.code, self.force_refresh)
                    else:
                        return asset, self.tefas_service.fetch_current_price(asset.code, self.force_refresh)

                # Fetch prices concurrently
                prices = {}
                with ThreadPoolExecutor(max_workers=10) as executor:
                    results = executor.map(fetch_price, assets)
                    for asset, price in results:
                        prices[asset.id] = price or 0.0

                for asset in assets:
                    current_price = prices.get(asset.id, 0.0)
                    
                    txs = asset.transactions
                    stats = PortfolioService.calculate_cost_and_pnl(txs, current_price, method=self.cost_method)
                    
                    if stats["remaining_quantity"] > 0:
                        current_value = stats["remaining_quantity"] * current_price
                        total_value_try += current_value
                        total_cost_try += stats["total_cost"]
                        realized_pnl_total += stats["realized_pnl"]
                        unrealized_pnl_total += stats["unrealized_pnl"]
                        
                        portfolio_items.append({
                            "id": asset.id,
                            "code": asset.code,
                            "name": asset.name,
                            "type": asset.asset_type.name,
                            "quantity": stats["remaining_quantity"],
                            "avg_cost": stats["average_cost"],
                            "current_price": current_price,
                            "total_cost": stats["total_cost"],
                            "current_value": current_value,
                            "realized_pnl": stats["realized_pnl"],
                            "unrealized_pnl": stats["unrealized_pnl"]
                        })

                # Portföy yüzdesi hesapla
                for item in portfolio_items:
                    item["portfolio_pct"] = (item["current_value"] / total_value_try * 100) if total_value_try > 0 else 0
                
                total_pnl = realized_pnl_total + unrealized_pnl_total
                pnl_pct = (total_pnl / total_cost_try * 100) if total_cost_try > 0 else 0
                
                kpi_data = {
                    "total_value_try": total_value_try,
                    "total_cost_try": total_cost_try,
                    "realized_pnl": realized_pnl_total,
                    "unrealized_pnl": unrealized_pnl_total,
                    "total_pnl": total_pnl,
                    "pnl_pct": pnl_pct,
                    "portfolio_items": portfolio_items
                }
                self.data_loaded_signal.emit(portfolio_items, kpi_data)
                
        except Exception as e:
            app_logger.error(f"Error in loader thread: {e}")
            self.error_signal.emit(str(e))

class PortfolioViewModel(QObject):
    # Signals
    data_loaded = Signal(list)
    error_occurred = Signal(str)
    loading_started = Signal()
    loading_finished = Signal()
    kpi_updated = Signal(dict)

    def __init__(self):
        super().__init__()
        self.bist_service = BistService()
        self.tefas_service = TefasService()
        self.cached_portfolio_data = []
        self._thread = None

    def load_data(self, cost_method="WAC", force_refresh=False):
        self.loading_started.emit()
        self._thread = PortfolioLoaderThread(cost_method, force_refresh, self.bist_service, self.tefas_service)
        self._thread.data_loaded_signal.connect(self._on_data_loaded_success)
        self._thread.error_signal.connect(self._on_data_loaded_error)
        self._thread.finished.connect(lambda: self.loading_finished.emit())
        self._thread.start()

    @Slot(list, dict)
    def _on_data_loaded_success(self, items, kpi_data):
        self.cached_portfolio_data = items
        self.data_loaded.emit(items)
        self.kpi_updated.emit(kpi_data)

    @Slot(str)
    def _on_data_loaded_error(self, err):
        self.error_occurred.emit(err)

    def add_asset(self, code: str, name: str, a_type: str):
        try:
            with get_session() as session:
                asset_type = AssetType.BIST if a_type == "BIST" else AssetType.TEFAS
                existing = session.query(Asset).filter_by(code=code.upper()).first()
                if not existing:
                    new_asset = Asset(code=code.upper(), name=name, asset_type=asset_type)
                    session.add(new_asset)
                    session.commit()
            self.load_data()
        except Exception as e:
            app_logger.error(f"Error adding asset: {e}")
            self.error_occurred.emit(str(e))

    def add_transaction(self, **kwargs):
        try:
            with get_session() as session:
                from app.models.transaction import Transaction, TransactionType
                tx = Transaction(
                    asset_id=kwargs["asset_id"],
                    transaction_type=TransactionType[kwargs["tx_type"]],
                    date=kwargs["date"],
                    quantity=kwargs["quantity"],
                    unit_price=kwargs["unit_price"],
                    commission=kwargs.get("commission", 0) or 0,
                    tax=kwargs.get("tax", 0) or 0,
                    note=kwargs.get("note", "")
                )
                session.add(tx)
                session.commit()
            self.load_data()
        except Exception as e:
            app_logger.error(f"Error adding transaction: {e}")
            self.error_occurred.emit(str(e))

    def get_recent_transactions(self, limit=5):
        try:
            with get_session() as session:
                from app.models.transaction import Transaction
                from sqlalchemy import desc
                txs = session.query(Transaction).order_by(desc(Transaction.date), desc(Transaction.id)).limit(limit).all()
                result = []
                for tx in txs:
                    result.append({
                        "id": tx.id,
                        "date": tx.date.strftime("%Y-%m-%d"),
                        "asset_code": tx.asset.code,
                        "type": tx.transaction_type.name,
                        "quantity": tx.quantity,
                        "unit_price": tx.unit_price,
                        "total": (tx.quantity * tx.unit_price) + tx.commission + tx.tax,
                        "note": tx.note
                    })
                return result
        except Exception as e:
            app_logger.error(f"Error fetching recent txs: {e}")
            return []
