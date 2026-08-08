from PySide6.QtCore import QObject, Signal
from sqlalchemy.orm import joinedload

from app.database.session import get_session
from app.models.asset import Asset
from app.models.transaction import Transaction, TransactionType
from app.services.transaction_service import TransactionCommand, TransactionService
from app.utils.logger import app_logger


class TransactionViewModel(QObject):
    transactions_loaded = Signal(list)
    action_success = Signal(str)
    action_failed = Signal(str)

    def __init__(self):
        super().__init__()
        self.selected_portfolio_id = 1

    def set_portfolio(self, portfolio_id):
        self.selected_portfolio_id = int(portfolio_id) if portfolio_id is not None else None
        self.load_transactions()

    def load_transactions(self):
        try:
            with get_session() as session:
                txs = (
                    session.query(Transaction)
                    .options(joinedload(Transaction.asset))
                    .filter(
                        True
                        if self.selected_portfolio_id is None
                        else Transaction.portfolio_id == self.selected_portfolio_id
                    )
                    .order_by(Transaction.date.desc(), Transaction.id.desc())
                    .all()
                )
                result = []
                for tx in txs:
                    gross = float(tx.quantity) * float(tx.unit_price)
                    fees = float(tx.commission) + float(tx.tax)
                    if tx.transaction_type == TransactionType.BUY:
                        total = gross + fees
                    elif tx.transaction_type == TransactionType.SPLIT:
                        total = 0.0  # nakit akışı yok
                    else:  # SELL, DIVIDEND => net nakit girişi
                        total = gross - fees
                    result.append({
                        "id": tx.id,
                        "portfolio_id": tx.portfolio_id,
                        "asset_id": tx.asset_id,
                        "date": tx.date.strftime("%Y-%m-%d"),
                        "date_obj": tx.date,
                        "asset_code": tx.asset.code if tx.asset else "?",
                        "type": tx.transaction_type.name,
                        "quantity": float(tx.quantity),
                        "unit_price": float(tx.unit_price),
                        "commission": float(tx.commission),
                        "tax": float(tx.tax),
                        "total": total,
                        "note": tx.note or "",
                    })
                self.transactions_loaded.emit(result)
        except Exception as e:
            app_logger.error(f"Load transactions error: {e}")
            self.action_failed.emit(str(e))

    def add_transaction(self, asset_id, tx_type, date, quantity, unit_price, commission, tax, note):
        try:
            if self.selected_portfolio_id is None:
                raise ValueError("İşlem eklemek için belirli bir portföy seçin.")
            with get_session() as session:
                command = TransactionCommand.from_values(
                    portfolio_id=self.selected_portfolio_id,
                    asset_id=asset_id,
                    transaction_type=tx_type,
                    date=date,
                    quantity=quantity,
                    unit_price=unit_price,
                    commission=commission,
                    tax=tax,
                    note=note,
                )
                with session.begin():
                    TransactionService.create(session, command)
            self.action_success.emit("İşlem başarıyla eklendi.")
            self.load_transactions()
        except Exception as e:
            app_logger.error(f"Add transaction error: {e}")
            self.action_failed.emit(str(e))

    def update_transaction(self, tx_id, asset_id, tx_type, date, quantity, unit_price, commission, tax, note):
        try:
            if self.selected_portfolio_id is None:
                raise ValueError("İşlem güncellemek için belirli bir portföy seçin.")
            with get_session() as session:
                command = TransactionCommand.from_values(
                    portfolio_id=self.selected_portfolio_id,
                    asset_id=asset_id,
                    transaction_type=tx_type,
                    date=date,
                    quantity=quantity,
                    unit_price=unit_price,
                    commission=commission,
                    tax=tax,
                    note=note,
                )
                with session.begin():
                    TransactionService.update(session, tx_id, command)
            self.action_success.emit("İşlem güncellendi.")
            self.load_transactions()
        except Exception as e:
            app_logger.error(f"Update transaction error: {e}")
            self.action_failed.emit(str(e))

    def delete_transaction(self, tx_id):
        try:
            with get_session() as session:
                with session.begin():
                    TransactionService.delete(session, tx_id)
            self.action_success.emit("İşlem silindi.")
            self.load_transactions()
        except Exception as e:
            app_logger.error(f"Delete transaction error: {e}")
            self.action_failed.emit(str(e))

    def get_available_assets(self):
        try:
            with get_session() as session:
                return [{"id": a.id, "code": a.code} for a in session.query(Asset).all()]
        except Exception as e:
            app_logger.error(f"Get available assets error: {e}")
            return []

    def shutdown(self) -> None:
        """Bu ViewModel arka plan işçisi tutmaz; ortak kapanış sözleşmesini uygular."""
