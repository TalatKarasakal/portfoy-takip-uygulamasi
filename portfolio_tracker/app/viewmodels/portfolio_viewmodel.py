import datetime
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass

from PySide6.QtCore import QObject, QThread, Signal, Slot
from sqlalchemy.orm import joinedload

from app.database.session import get_session
from app.models.asset import Asset, AssetType
from app.models.settings import Settings
from app.models.transaction import Transaction
from app.services.bist_service import BistService
from app.services.currency_service import CurrencyService
from app.services.portfolio_account_service import PortfolioAccountService
from app.services.portfolio_service import PortfolioCalculationError, PortfolioService
from app.services.price_history_service import PriceHistoryService
from app.services.pricing_types import DataFreshness, QuoteResult
from app.services.refresh_policy import RefreshPolicy
from app.services.snapshot_service import SnapshotService
from app.services.tefas_service import TefasService
from app.services.transaction_service import TransactionCommand, TransactionService
from app.utils.display import display
from app.utils.logger import app_logger
from app.viewmodels.worker import FunctionWorker, stop_worker


@dataclass(frozen=True)
class PortfolioLoadRequest:
    cost_method: str
    force_refresh: bool
    portfolio_id: int | None
    allow_bist_network: bool
    allow_tefas_network: bool


class PortfolioLoaderThread(QThread):
    data_loaded_signal = Signal(list, dict)
    error_signal = Signal(str)

    def __init__(self, request: PortfolioLoadRequest):
        super().__init__()
        self.request = request

    def run(self):
        try:
            bist_service = BistService()
            tefas_service = TefasService()
            currency_service = CurrencyService()
            with get_session() as session:
                asset_query = session.query(Asset).options(joinedload(Asset.transactions))
                if self.request.portfolio_id is not None:
                    asset_query = (
                        asset_query.join(Transaction)
                        .filter(Transaction.portfolio_id == self.request.portfolio_id)
                        .distinct()
                    )
                else:
                    asset_query = asset_query.join(Transaction).distinct()
                assets = asset_query.all()
                portfolio_items = []

                total_value_try = 0.0
                total_cost_try = 0.0
                realized_pnl_total = 0.0
                unrealized_pnl_total = 0.0
                daily_change_total = 0.0
                prev_value_total = 0.0
                failed_codes = []
                stale_codes = []
                connection_error_codes = []
                scheduled_codes = []
                invalid_codes = []

                def fetch_asset_quote(asset_data):
                    asset_id, code, asset_type = asset_data
                    try:
                        if asset_type == AssetType.BIST.name:
                            q = bist_service.fetch_quote(
                                code,
                                self.request.force_refresh,
                                self.request.allow_bist_network,
                            )
                        else:
                            q = tefas_service.fetch_quote(
                                code,
                                self.request.force_refresh,
                                self.request.allow_tefas_network,
                            )
                        return asset_id, q
                    except Exception as ex:
                        app_logger.error(f"Error fetching quote for {code}: {ex}")
                        return asset_id, QuoteResult(
                            None,
                            None,
                            "bilinmiyor",
                            None,
                            datetime.datetime.now(datetime.timezone.utc),
                            DataFreshness.OFFLINE,
                            str(ex),
                        )

                quotes_map = {}
                quote_inputs = [(asset.id, asset.code, asset.asset_type.name) for asset in assets]
                with ThreadPoolExecutor(max_workers=10) as executor:
                    results = executor.map(fetch_asset_quote, quote_inputs)
                    for asset_id, q in results:
                        quotes_map[asset_id] = q

                for asset in assets:
                    quote = quotes_map[asset.id]
                    if asset.asset_type == AssetType.TEFAS:
                        # Fon adı henüz çözülmemişse (ad == kod) TEFAS'tan tam adı çek
                        if not asset.name or asset.name == asset.code:
                            fund_name = tefas_service.fetch_fund_name(asset.code)
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

                    txs = [
                        tx
                        for tx in asset.transactions
                        if self.request.portfolio_id is None
                        or tx.portfolio_id == self.request.portfolio_id
                    ]
                    try:
                        stats = PortfolioService.calculate_cost_and_pnl(
                            txs, current_price, method=self.request.cost_method
                        )
                    except PortfolioCalculationError as exc:
                        invalid_codes.append(f"{asset.code}: {exc}")
                        continue

                    # Gerçekleşmiş K/Z tüm varlıklar için toplanır (tamamen satılmış
                    # pozisyonların kârı da dahil; aksi halde portföyden tamamen çıkılan
                    # pozisyonların kazancı kaybolurdu).
                    realized_pnl_total += stats["realized_pnl"]

                    if stats["remaining_quantity"] > 0:
                        if current_price <= 0:
                            if quote.error and "bek" in quote.error.lower():
                                scheduled_codes.append(asset.code)
                            elif quote.error and "bulunamadı" not in quote.error.lower():
                                connection_error_codes.append(asset.code)
                            else:
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
                            "price_source": quote.source,
                            "price_date": quote.price_date,
                            "price_fetched_at": quote.fetched_at,
                            "price_status": (
                                DataFreshness.STALE.value if is_stale else quote.status.value
                            ),
                            "price_error": quote.error,
                        })

                securities_value_try = total_value_try
                cash_balance = float(
                    PortfolioAccountService.cash_balance(session, self.request.portfolio_id)
                )
                total_value_try = securities_value_try + cash_balance

                # Portföy yüzdesi, nakit dahil toplam değer üzerinden hesaplanır.
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
                usd_try = currency_service.fetch_usd_try(self.request.force_refresh)
                total_value_usd = (total_value_try / usd_try) if usd_try else 0.0

                # En iyi / en kötü pozisyon (toplam K/Z yüzdesine göre)
                best = None
                worst = None
                if portfolio_items:
                    best = max(portfolio_items, key=lambda x: x["pnl_pct"])
                    worst = min(portfolio_items, key=lambda x: x["pnl_pct"])

                # Günlük snapshot kaydı (gerçek zaman serisi grafikleri için)
                if total_value_try > 0 and self.request.portfolio_id is not None:
                    SnapshotService.record_snapshot(
                        session,
                        total_value_try=total_value_try,
                        total_cost_try=total_cost_try,
                        unrealized_pnl_try=unrealized_pnl_total,
                        total_value_usd=total_value_usd,
                        portfolio_id=self.request.portfolio_id,
                        cash_balance_try=cash_balance,
                        net_external_flow_try=float(
                            PortfolioAccountService.external_flow_for_date(
                                session, self.request.portfolio_id, datetime.date.today()
                            )
                        ),
                    )

                # Zaman serisi geçmişi (dashboard küçük grafik)
                history = (
                    SnapshotService.get_history(
                        session, days=90, portfolio_id=self.request.portfolio_id
                    )
                    if self.request.portfolio_id is not None
                    else SnapshotService.get_consolidated_history(session, days=90)
                )

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
                    "connection_error_codes": connection_error_codes,
                    "scheduled_codes": scheduled_codes,
                    "invalid_codes": invalid_codes,
                    "history": history,
                    "portfolio_items": portfolio_items,
                    "portfolio_id": self.request.portfolio_id,
                    "cash_balance_try": cash_balance,
                    "securities_value_try": securities_value_try,
                    "tefas_network_attempted": self.request.allow_tefas_network
                    and any(asset.asset_type == AssetType.TEFAS for asset in assets),
                }
                if not self.isInterruptionRequested():
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
    portfolios_loaded = Signal(list)
    portfolio_selection_changed = Signal(object)
    asset_history_loaded = Signal(str, list)
    asset_history_failed = Signal(str, str)

    def __init__(self):
        super().__init__()
        self.cached_portfolio_data = []
        self.cached_kpi_data = {}
        self.cost_method = self._load_cost_method()
        self._thread = None
        self._reload_pending = False
        self._pending_force_refresh = False
        self._history_workers: dict[str, FunctionWorker] = {}
        self.selected_portfolio_id = 1
        self.refresh_policy = RefreshPolicy()

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
        # Bir yükleme sürerken yenisini başlatma: çalışan QThread'in son referansı
        # kaybolup yok edilirse Qt "Destroyed while running" ile uygulamayı
        # çökertir. Bunun yerine mevcut yükleme bitince bir kez yeniden çalış.
        if self._thread is not None and self._thread.isRunning():
            self._reload_pending = True
            self._pending_force_refresh = self.merge_force_refresh(
                self._pending_force_refresh, force_refresh
            )
            return
        method = cost_method or self.cost_method
        refresh_plan = self.refresh_policy.plan(force_refresh)
        self.loading_started.emit()
        self._thread = PortfolioLoaderThread(
            PortfolioLoadRequest(
                method,
                force_refresh,
                self.selected_portfolio_id,
                refresh_plan.allow_bist_network,
                refresh_plan.allow_tefas_network,
            )
        )
        self._thread.data_loaded_signal.connect(self._on_data_loaded_success)
        self._thread.error_signal.connect(self._on_data_loaded_error)
        self._thread.finished.connect(self._on_loader_finished)
        self._thread.start()

    @staticmethod
    def merge_force_refresh(current: bool, incoming: bool) -> bool:
        """Bekleyen zorunlu isteğin normal bir istek tarafından düşürülmesini önler."""
        return current or incoming

    def _on_loader_finished(self):
        self.loading_finished.emit()
        # Yükleme sürerken gelen bir yenileme isteği biriktiyse şimdi çalıştır.
        if self._reload_pending:
            self._reload_pending = False
            force_refresh = self._pending_force_refresh
            self._pending_force_refresh = False
            self.load_data(force_refresh=force_refresh)

    @Slot(list, dict)
    def _on_data_loaded_success(self, items, kpi_data):
        self.cached_portfolio_data = items
        self.cached_kpi_data = kpi_data
        if kpi_data.get("tefas_network_attempted"):
            self.refresh_policy.mark_tefas_refreshed()
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

    def configure_refresh_policy(self, overrides_json: str) -> None:
        self.refresh_policy.configure(overrides_json)

    @Slot(str)
    def _on_data_loaded_error(self, err):
        self.error_occurred.emit(err)

    def add_asset(self, code: str, name: str, a_type: str, quantity=None, unit_price=None):
        """Varlık ekler. İsteğe bağlı adet + alış fiyatı verilirse, varlığın
        portföyde hemen görünmesi için bir açılış (BUY) işlemi de oluşturur.
        """
        try:
            with get_session() as session:
                asset_type = AssetType.BIST if a_type == "BIST" else AssetType.TEFAS
                asset = TransactionService.get_or_create_asset(
                    session, code, name=name, asset_type=asset_type
                )

                # İsteğe bağlı açılış işlemi (adet ve fiyat girildiyse)
                try:
                    q = float(quantity) if quantity not in (None, "") else 0.0
                    p = float(unit_price) if unit_price not in (None, "") else 0.0
                except (TypeError, ValueError):
                    q = p = 0.0
                if q > 0 and p > 0:
                    from datetime import date as _date

                    command = TransactionCommand.from_values(
                        portfolio_id=self._require_concrete_portfolio(),
                        asset_id=asset.id,
                        transaction_type="BUY",
                        date=_date.today(),
                        quantity=q,
                        unit_price=p,
                        note="Açılış (varlık eklerken)",
                    )
                    TransactionService.create(session, command)
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
        """Seçili portföydeki varlık işlemlerini siler; ortak kataloğu korur."""
        try:
            portfolio_id = self._require_concrete_portfolio()
            with get_session() as session:
                session.query(Transaction).filter_by(
                    asset_id=asset_id, portfolio_id=portfolio_id
                ).delete(synchronize_session=False)
                session.commit()
            self.load_data()
        except Exception as e:
            app_logger.error(f"Error deleting asset: {e}")
            self.error_occurred.emit(str(e))

    def add_transaction(self, **kwargs):
        try:
            with get_session() as session:
                command = TransactionCommand.from_values(
                    portfolio_id=self._require_concrete_portfolio(),
                    asset_id=kwargs["asset_id"],
                    transaction_type=kwargs["tx_type"],
                    date=kwargs["date"],
                    quantity=kwargs["quantity"],
                    unit_price=kwargs["unit_price"],
                    commission=kwargs.get("commission", 0) or 0,
                    tax=kwargs.get("tax", 0) or 0,
                    note=kwargs.get("note", ""),
                )
                with session.begin():
                    TransactionService.create(session, command)
            self.load_data()
        except Exception as e:
            app_logger.error(f"Error adding transaction: {e}")
            self.error_occurred.emit(str(e))

    def get_recent_transactions(self, limit=5):
        try:
            with get_session() as session:
                from sqlalchemy import desc
                from sqlalchemy.orm import joinedload

                from app.models.transaction import Transaction, TransactionType
                txs = (
                    session.query(Transaction)
                    .options(joinedload(Transaction.asset))
                    .filter(
                        True
                        if self.selected_portfolio_id is None
                        else Transaction.portfolio_id == self.selected_portfolio_id
                    )
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
                        "commission": float(tx.commission),
                        "tax": float(tx.tax),
                        "total": total,
                        "note": tx.note or ""
                    })
                return result
        except Exception as e:
            app_logger.error(f"Error fetching recent txs: {e}")
            return []

    def _require_concrete_portfolio(self) -> int:
        if self.selected_portfolio_id is None:
            raise ValueError("İşlem yapmak için belirli bir portföy seçin.")
        return self.selected_portfolio_id

    def load_portfolios(self) -> None:
        try:
            with get_session() as session:
                rows = PortfolioAccountService.list_portfolios(session)
            self.portfolios_loaded.emit(rows)
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def create_portfolio(self, name: str) -> None:
        try:
            with get_session() as session:
                with session.begin():
                    row = PortfolioAccountService.create_portfolio(session, name)
                    portfolio_id = row.id
            self.selected_portfolio_id = portfolio_id
            self.load_portfolios()
            self.portfolio_selection_changed.emit(portfolio_id)
            self.load_data()
        except Exception as exc:
            self.error_occurred.emit(str(exc))

    def set_portfolio(self, portfolio_id) -> None:
        normalized = int(portfolio_id) if portfolio_id is not None else None
        if normalized == self.selected_portfolio_id:
            return
        self.selected_portfolio_id = normalized
        self.portfolio_selection_changed.emit(normalized)
        self.load_data()

    def load_asset_history(self, code: str, asset_type: str) -> None:
        request = (code, asset_type)
        tag = f"asset-history:{code}"
        current = self._history_workers.get(tag)
        if current is not None and current.isRunning():
            return

        def task():
            records = []
            if request[1] == "BIST":
                raw = BistService().fetch_historical_prices(request[0], period="1y")
                records = [
                    {"date": row["date"], "price": row["close_price"]} for row in raw
                ]
            else:
                end = datetime.datetime.now()
                start = end - datetime.timedelta(days=365)
                raw = TefasService().fetch_historical_prices(request[0], start, end)
                records = [
                    {"date": row.get("date"), "price": float(row["price"])}
                    for row in raw
                    if row.get("date") is not None and row.get("price") is not None
                ]
            records.sort(key=lambda row: row["date"])
            return request[0], records

        worker = FunctionWorker(tag, task)
        worker.result_ready.connect(
            lambda _tag, result: self.asset_history_loaded.emit(result[0], result[1])
        )
        worker.error_occurred.connect(
            lambda _tag, message: self.asset_history_failed.emit(request[0], message)
        )
        worker.finished.connect(lambda: self._history_workers.pop(tag, None))
        self._history_workers[tag] = worker
        worker.start()

    def shutdown(self) -> None:
        stop_worker(self._thread)
        for worker in list(self._history_workers.values()):
            stop_worker(worker)
        self._history_workers.clear()
