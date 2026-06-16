from PySide6.QtCore import QObject, Signal, Slot, QThread
from app.database.session import get_session
from app.models.asset import Asset, AssetType
from app.models.settings import Settings
from app.services.bist_service import BistService
from app.services.tefas_service import TefasService
from app.services.currency_service import CurrencyService
from app.services.portfolio_service import PortfolioService
from app.services.snapshot_service import SnapshotService
from app.services.price_history_service import PriceHistoryService
from app.utils.display import display
from app.utils.logger import app_logger


class PortfolioLoaderThread(QThread):
    data_loaded_signal = Signal(list, dict)
    error_signal = Signal(str)

    def __init__(self, cost_method, force_refresh, bist_service, tefas_service, currency_service):
        super().__init__()
        self.cost_method = cost_method
        self.force_refresh = force_refresh
        self.bist_service = bist_service
        self.tefas_service = tefas_service
        self.currency_service = currency_service

    def run(self):
        try:
            with get_session() as session:
                assets = session.query(Asset).all()
                portfolio_items = []

                total_value_try = 0.0
                total_cost_try = 0.0
                realized_pnl_total = 0.0
                unrealized_pnl_total = 0.0
                daily_change_total = 0.0
                prev_value_total = 0.0
                failed_codes = []
                stale_codes = []

                for asset in assets:
                    if asset.asset_type == AssetType.BIST:
                        quote = self.bist_service.fetch_quote(asset.code, self.force_refresh)
                    else:
                        quote = self.tefas_service.fetch_quote(asset.code, self.force_refresh)
                        # Fon adı henüz çözülmemişse (ad == kod) TEFAS'tan tam adı çek
                        if not asset.name or asset.name == asset.code:
                            fund_name = self.tefas_service.fetch_fund_name(asset.code)
                            if fund_name:
                                asset.name = fund_name
                                session.commit()

                    current_price = quote.get("price") or 0.0
                    prev_close = quote.get("prev_close")
                    if prev_close is None:
                        prev_close = current_price

                    is_stale = False
                    if current_price > 0:
                        # Güncel fiyatı ileride yedek olarak kullanmak üzere sakla
                        PriceHistoryService.record_close(session, asset.id, current_price)
                    else:
                        # Her iki kaynak da başarısız: son bilinen fiyata düş
                        last = PriceHistoryService.last_close(session, asset.id)
                        if last:
                            current_price = last
                            prev_close = last  # değişim hesaplanamaz
                            is_stale = True

                    txs = asset.transactions
                    stats = PortfolioService.calculate_cost_and_pnl(txs, current_price, method=self.cost_method)

                    # Gerçekleşmiş K/Z tüm varlıklar için toplanır (tamamen satılmış
                    # pozisyonların kârı da dahil; aksi halde portföyden tamamen çıkılan
                    # pozisyonların kazancı kaybolurdu).
                    realized_pnl_total += stats["realized_pnl"]

                    if stats["remaining_quantity"] > 0:
                        if current_price <= 0:
                            failed_codes.append(asset.code)
                        elif is_stale:
                            stale_codes.append(asset.code)

                    if stats["remaining_quantity"] > 0:
                        qty = stats["remaining_quantity"]
                        current_value = qty * current_price
                        item_daily_change = (current_price - prev_close) * qty
                        item_pnl = stats["realized_pnl"] + stats["unrealized_pnl"]
                        item_pnl_pct = (
                            (item_pnl / stats["total_cost"] * 100) if stats["total_cost"] > 0 else 0.0
                        )

                        total_value_try += current_value
                        total_cost_try += stats["total_cost"]
                        unrealized_pnl_total += stats["unrealized_pnl"]
                        daily_change_total += item_daily_change
                        prev_value_total += prev_close * qty

                        portfolio_items.append({
                            "id": asset.id,
                            "code": asset.code,
                            "name": asset.name,
                            "type": asset.asset_type.name,
                            "quantity": qty,
                            "avg_cost": stats["average_cost"],
                            "current_price": current_price,
                            "prev_close": prev_close,
                            "total_cost": stats["total_cost"],
                            "current_value": current_value,
                            "daily_change": item_daily_change,
                            "realized_pnl": stats["realized_pnl"],
                            "unrealized_pnl": stats["unrealized_pnl"],
                            "pnl": item_pnl,
                            "pnl_pct": item_pnl_pct,
                        })

                # Portföy yüzdesi hesapla
                for item in portfolio_items:
                    item["portfolio_pct"] = (
                        (item["current_value"] / total_value_try * 100) if total_value_try > 0 else 0
                    )

                total_pnl = realized_pnl_total + unrealized_pnl_total
                pnl_pct = (total_pnl / total_cost_try * 100) if total_cost_try > 0 else 0
                daily_change_pct = (
                    (daily_change_total / prev_value_total * 100) if prev_value_total > 0 else 0
                )

                # USD karşılığı (TCMB kuru). Kur alınamazsa 0 kalır.
                usd_try = self.currency_service.fetch_usd_try(self.force_refresh)
                total_value_usd = (total_value_try / usd_try) if usd_try else 0.0

                # En iyi / en kötü pozisyon (toplam K/Z yüzdesine göre)
                best = None
                worst = None
                if portfolio_items:
                    best = max(portfolio_items, key=lambda x: x["pnl_pct"])
                    worst = min(portfolio_items, key=lambda x: x["pnl_pct"])

                # Günlük snapshot kaydı (gerçek zaman serisi grafikleri için)
                if total_value_try > 0:
                    SnapshotService.record_snapshot(
                        session,
                        total_value_try=total_value_try,
                        total_cost_try=total_cost_try,
                        unrealized_pnl_try=unrealized_pnl_total,
                        total_value_usd=total_value_usd,
                    )

                # Zaman serisi geçmişi (dashboard küçük grafik)
                history = SnapshotService.get_history(session, days=90)

                kpi_data = {
                    "total_value_try": total_value_try,
                    "total_value_usd": total_value_usd,
                    "usd_try": usd_try or 0.0,
                    "total_cost_try": total_cost_try,
                    "realized_pnl": realized_pnl_total,
                    "unrealized_pnl": unrealized_pnl_total,
                    "total_pnl": total_pnl,
                    "pnl_pct": pnl_pct,
                    "daily_change_try": daily_change_total,
                    "daily_change_pct": daily_change_pct,
                    "best": {"code": best["code"], "pnl_pct": best["pnl_pct"]} if best else None,
                    "worst": {"code": worst["code"], "pnl_pct": worst["pnl_pct"]} if worst else None,
                    "failed_codes": failed_codes,
                    "stale_codes": stale_codes,
                    "history": history,
                    "portfolio_items": portfolio_items,
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
        self.currency_service = CurrencyService()
        self.cached_portfolio_data = []
        self.cached_kpi_data = {}
        self.cost_method = self._load_cost_method()
        self._thread = None

    def _load_cost_method(self) -> str:
        """Aktif maliyet metodunu (WAC/FIFO/LIFO) ayarlardan okur."""
        try:
            with get_session() as session:
                row = session.query(Settings).filter_by(key="cost_method").first()
                if row and row.value in ("WAC", "FIFO", "LIFO"):
                    return row.value
        except Exception as e:
            app_logger.error(f"Cost method okunamadı: {e}")
        return "WAC"

    def set_cost_method(self, method: str):
        """Maliyet metodunu güncelle ve portföyü yeniden hesapla."""
        if method in ("WAC", "FIFO", "LIFO") and method != self.cost_method:
            self.cost_method = method
            self.load_data()

    def load_data(self, cost_method=None, force_refresh=False):
        method = cost_method or self.cost_method
        self.loading_started.emit()
        self._thread = PortfolioLoaderThread(
            method, force_refresh, self.bist_service, self.tefas_service, self.currency_service
        )
        self._thread.data_loaded_signal.connect(self._on_data_loaded_success)
        self._thread.error_signal.connect(self._on_data_loaded_error)
        self._thread.finished.connect(lambda: self.loading_finished.emit())
        self._thread.start()

    @Slot(list, dict)
    def _on_data_loaded_success(self, items, kpi_data):
        self.cached_portfolio_data = items
        self.cached_kpi_data = kpi_data
        # Görüntüleme kuru güncellensin ki view'lar doğru çevirsin
        display.set_rate(kpi_data.get("usd_try", 0))
        self.data_loaded.emit(items)
        self.kpi_updated.emit(kpi_data)

    def refresh_display(self):
        """Para birimi/biçim değişiminde önbellekteki veriyle yeniden render eder
        (ağdan tekrar çekmeden)."""
        if self.cached_kpi_data:
            display.set_rate(self.cached_kpi_data.get("usd_try", 0))
        self.data_loaded.emit(self.cached_portfolio_data)
        if self.cached_kpi_data:
            self.kpi_updated.emit(self.cached_kpi_data)

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

    def update_asset(self, asset_id: int, name: str, a_type: str):
        """Varlığın adını ve türünü günceller."""
        try:
            with get_session() as session:
                asset = session.query(Asset).filter_by(id=asset_id).first()
                if asset:
                    asset.name = name
                    asset.asset_type = AssetType.BIST if a_type == "BIST" else AssetType.TEFAS
                    session.commit()
            self.load_data()
        except Exception as e:
            app_logger.error(f"Error updating asset: {e}")
            self.error_occurred.emit(str(e))

    def delete_asset(self, asset_id: int):
        """Varlığı ve ona bağlı tüm işlem/uyarı/fiyat kayıtlarını siler."""
        try:
            with get_session() as session:
                asset = session.query(Asset).filter_by(id=asset_id).first()
                if asset:
                    session.delete(asset)
                    session.commit()
            self.load_data()
        except Exception as e:
            app_logger.error(f"Error deleting asset: {e}")
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
                from app.models.transaction import Transaction, TransactionType
                from sqlalchemy import desc
                from sqlalchemy.orm import joinedload
                txs = (
                    session.query(Transaction)
                    .options(joinedload(Transaction.asset))
                    .order_by(desc(Transaction.date), desc(Transaction.id))
                    .limit(limit)
                    .all()
                )
                result = []
                for tx in txs:
                    gross = float(tx.quantity) * float(tx.unit_price)
                    fees = float(tx.commission) + float(tx.tax)
                    # Alımda masraflar toplam maliyeti artırır; satım/temettüde net geliri düşürür.
                    if tx.transaction_type == TransactionType.BUY:
                        total = gross + fees
                    elif tx.transaction_type == TransactionType.SPLIT:
                        total = 0.0
                    else:
                        total = gross - fees
                    result.append({
                        "id": tx.id,
                        "date": tx.date.strftime("%Y-%m-%d"),
                        "asset_code": tx.asset.code,
                        "type": tx.transaction_type.name,
                        "quantity": float(tx.quantity),
                        "unit_price": float(tx.unit_price),
                        "total": total,
                        "note": tx.note
                    })
                return result
        except Exception as e:
            app_logger.error(f"Error fetching recent txs: {e}")
            return []
