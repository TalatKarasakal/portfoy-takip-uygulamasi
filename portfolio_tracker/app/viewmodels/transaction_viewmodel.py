from PySide6.QtCore import QObject, Signal
from sqlalchemy.orm import joinedload
from app.database.session import get_session
from app.models.transaction import Transaction, TransactionType
from app.models.asset import Asset
from app.utils.logger import app_logger

class TransactionViewModel(QObject):
    transactions_loaded = Signal(list)
    action_success = Signal(str)
    action_failed = Signal(str)

    def load_transactions(self):
        try:
            with get_session() as session:
                txs = session.query(Transaction).options(joinedload(Transaction.asset)).order_by(Transaction.date.desc()).all()
                result = []
                for tx in txs:
                    result.append({
                        "id": tx.id,
                        "date": tx.date.strftime("%Y-%m-%d"),
                        "asset_code": tx.asset.code,
                        "type": tx.transaction_type.name,
                        "quantity": float(tx.quantity),
                        "unit_price": float(tx.unit_price),
                        "commission": float(tx.commission),
                        "tax": float(tx.tax),
                        "total": float(tx.total_cost) if tx.transaction_type == TransactionType.BUY else 
                                 (float(tx.quantity) * float(tx.unit_price) - float(tx.commission) - float(tx.tax)),
                        "note": tx.note
                    })
                self.transactions_loaded.emit(result)
        except Exception as e:
            app_logger.error(f"Load transactions error: {e}")
            self.action_failed.emit(str(e))

    def add_transaction(self, asset_id, tx_type, date, quantity, unit_price, commission, tax, note):
        try:
            with get_session() as session:
                tx = Transaction(
                    asset_id=asset_id,
                    transaction_type=TransactionType[tx_type],
                    date=date,
                    quantity=quantity,
                    unit_price=unit_price,
                    commission=commission,
                    tax=tax,
                    note=note
                )
                session.add(tx)
                session.commit()
            self.action_success.emit("İşlem başarıyla eklendi.")
            self.load_transactions()
        except Exception as e:
            app_logger.error(f"Add transaction error: {e}")
            self.action_failed.emit(str(e))

    def get_available_assets(self):
        try:
            with get_session() as session:
                return [{"id": a.id, "code": a.code} for a in session.query(Asset).all()]
        except Exception as e:
            app_logger.error(f"Get available assets error: {e}")
            return []
