"""Bütün işlem giriş kanalları için merkezi doğrulama ve kayıt servisi."""

from __future__ import annotations

import datetime
import enum
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Optional

from sqlalchemy.orm import Session

from app.models.asset import Asset, AssetType
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, TransactionType

ZERO = Decimal("0")
SIX_PLACES = Decimal("0.000001")


class TransactionErrorCode(enum.Enum):
    INVALID_PORTFOLIO = "invalid_portfolio"
    INVALID_ASSET = "invalid_asset"
    INVALID_TYPE = "invalid_type"
    INVALID_DATE = "invalid_date"
    FUTURE_DATE = "future_date"
    INVALID_QUANTITY = "invalid_quantity"
    INVALID_PRICE = "invalid_price"
    INVALID_FEES = "invalid_fees"
    INVALID_SPLIT = "invalid_split"
    OVERSELL = "oversell"
    NOT_FOUND = "not_found"


class TransactionValidationError(ValueError):
    def __init__(self, code: TransactionErrorCode, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


def _decimal(value, field_name: str) -> Decimal:
    try:
        result = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise TransactionValidationError(
            TransactionErrorCode.INVALID_PRICE,
            f"{field_name} geçerli bir sayı olmalıdır.",
        ) from exc
    if not result.is_finite():
        raise TransactionValidationError(
            TransactionErrorCode.INVALID_PRICE,
            f"{field_name} sonlu bir sayı olmalıdır.",
        )
    return result.quantize(SIX_PLACES)


@dataclass(frozen=True)
class TransactionCommand:
    portfolio_id: int
    asset_id: int
    transaction_type: TransactionType
    date: datetime.date
    quantity: Decimal
    unit_price: Decimal
    commission: Decimal = ZERO
    tax: Decimal = ZERO
    note: str = ""

    @classmethod
    def from_values(
        cls,
        *,
        portfolio_id,
        asset_id,
        transaction_type,
        date,
        quantity,
        unit_price,
        commission=0,
        tax=0,
        note="",
    ) -> "TransactionCommand":
        try:
            kind = (
                transaction_type
                if isinstance(transaction_type, TransactionType)
                else TransactionType[str(transaction_type).upper()]
            )
        except (KeyError, TypeError) as exc:
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_TYPE, "Geçersiz işlem türü."
            ) from exc
        if isinstance(date, datetime.datetime):
            date = date.date()
        if isinstance(date, str):
            try:
                date = datetime.date.fromisoformat(date)
            except ValueError as exc:
                raise TransactionValidationError(
                    TransactionErrorCode.INVALID_DATE, "Tarih YYYY-AA-GG biçiminde olmalıdır."
                ) from exc
        if not isinstance(date, datetime.date):
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_DATE, "Geçerli bir işlem tarihi gereklidir."
            )
        try:
            normalized_portfolio_id = int(portfolio_id)
            normalized_asset_id = int(asset_id)
        except (TypeError, ValueError) as exc:
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_ASSET, "Portföy ve varlık seçilmelidir."
            ) from exc
        return cls(
            portfolio_id=normalized_portfolio_id,
            asset_id=normalized_asset_id,
            transaction_type=kind,
            date=date,
            quantity=_decimal(quantity, "Adet"),
            unit_price=_decimal(unit_price, "Birim fiyat"),
            commission=_decimal(commission or 0, "Komisyon"),
            tax=_decimal(tax or 0, "Vergi"),
            note=str(note or "").strip()[:500],
        )


class TransactionService:
    @staticmethod
    def get_or_create_asset(
        session: Session,
        code: str,
        name: str = "",
        asset_type: AssetType | str = AssetType.BIST,
    ) -> Asset:
        normalized_code = str(code).strip().upper()
        if not normalized_code:
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_ASSET, "Varlık kodu boş olamaz."
            )
        kind = asset_type if isinstance(asset_type, AssetType) else AssetType[str(asset_type).upper()]
        asset = session.query(Asset).filter(Asset.code == normalized_code).first()
        if asset is None:
            asset = Asset(
                code=normalized_code,
                name=str(name).strip() or normalized_code,
                asset_type=kind,
            )
            session.add(asset)
            session.flush()
        return asset

    @staticmethod
    def validate_base(session: Session, command: TransactionCommand) -> None:
        if session.get(Portfolio, command.portfolio_id) is None:
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_PORTFOLIO, "Portföy bulunamadı."
            )
        if session.get(Asset, command.asset_id) is None:
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_ASSET, "Varlık bulunamadı."
            )
        if command.date > datetime.date.today():
            raise TransactionValidationError(
                TransactionErrorCode.FUTURE_DATE, "İşlem tarihi gelecekte olamaz."
            )
        if command.commission < ZERO or command.tax < ZERO:
            raise TransactionValidationError(
                TransactionErrorCode.INVALID_FEES, "Komisyon ve vergi negatif olamaz."
            )
        if command.transaction_type == TransactionType.SPLIT:
            if command.quantity != ZERO or command.unit_price <= ZERO or command.unit_price == Decimal("1"):
                raise TransactionValidationError(
                    TransactionErrorCode.INVALID_SPLIT,
                    "Bölünmede adet 0, oran pozitif ve 1'den farklı olmalıdır.",
                )
            if command.commission != ZERO or command.tax != ZERO:
                raise TransactionValidationError(
                    TransactionErrorCode.INVALID_SPLIT, "Bölünmede komisyon veya vergi olamaz."
                )
        else:
            if command.quantity <= ZERO:
                raise TransactionValidationError(
                    TransactionErrorCode.INVALID_QUANTITY, "Adet sıfırdan büyük olmalıdır."
                )
            if command.unit_price <= ZERO:
                raise TransactionValidationError(
                    TransactionErrorCode.INVALID_PRICE, "Birim fiyat sıfırdan büyük olmalıdır."
                )

    @staticmethod
    def _ledger_rows(
        session: Session,
        portfolio_id: int,
        asset_id: int,
        *,
        exclude_id: Optional[int] = None,
        pending: Optional[TransactionCommand] = None,
        pending_id: Optional[int] = None,
    ) -> list[tuple[datetime.date, int, TransactionType, Decimal, Decimal]]:
        query = session.query(Transaction).filter_by(
            portfolio_id=portfolio_id, asset_id=asset_id
        )
        if exclude_id is not None:
            query = query.filter(Transaction.id != exclude_id)
        rows = [
            (
                row.date,
                int(row.id),
                row.transaction_type,
                Decimal(str(row.quantity)),
                Decimal(str(row.unit_price)),
            )
            for row in query.all()
        ]
        if pending is not None:
            rows.append(
                (
                    pending.date,
                    pending_id if pending_id is not None else 2**63 - 1,
                    pending.transaction_type,
                    pending.quantity,
                    pending.unit_price,
                )
            )
        rows.sort(key=lambda item: (item[0], item[1]))
        return rows

    @staticmethod
    def validate_ledger(
        session: Session,
        portfolio_id: int,
        asset_id: int,
        *,
        exclude_id: Optional[int] = None,
        pending: Optional[TransactionCommand] = None,
        pending_id: Optional[int] = None,
    ) -> None:
        quantity = ZERO
        for tx_date, _tx_id, kind, tx_quantity, ratio in TransactionService._ledger_rows(
            session,
            portfolio_id,
            asset_id,
            exclude_id=exclude_id,
            pending=pending,
            pending_id=pending_id,
        ):
            if kind == TransactionType.BUY:
                quantity += tx_quantity
            elif kind == TransactionType.SELL:
                if tx_quantity > quantity:
                    raise TransactionValidationError(
                        TransactionErrorCode.OVERSELL,
                        f"{tx_date.isoformat()} tarihli satış eldeki {quantity} adedi aşıyor.",
                    )
                quantity -= tx_quantity
            elif kind == TransactionType.SPLIT:
                quantity *= ratio

    @staticmethod
    def create(session: Session, command: TransactionCommand) -> Transaction:
        TransactionService.validate_base(session, command)
        with session.no_autoflush:
            TransactionService.validate_ledger(
                session,
                command.portfolio_id,
                command.asset_id,
                pending=command,
            )
        row = Transaction(
            portfolio_id=command.portfolio_id,
            asset_id=command.asset_id,
            transaction_type=command.transaction_type,
            date=command.date,
            quantity=command.quantity,
            unit_price=command.unit_price,
            commission=command.commission,
            tax=command.tax,
            note=command.note or None,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def update(session: Session, transaction_id: int, command: TransactionCommand) -> Transaction:
        row = session.get(Transaction, transaction_id)
        if row is None:
            raise TransactionValidationError(
                TransactionErrorCode.NOT_FOUND, "İşlem bulunamadı."
            )
        TransactionService.validate_base(session, command)
        old_scope = (row.portfolio_id, row.asset_id)
        new_scope = (command.portfolio_id, command.asset_id)
        with session.no_autoflush:
            if old_scope != new_scope:
                TransactionService.validate_ledger(
                    session, old_scope[0], old_scope[1], exclude_id=row.id
                )
            TransactionService.validate_ledger(
                session,
                command.portfolio_id,
                command.asset_id,
                exclude_id=row.id,
                pending=command,
                pending_id=row.id,
            )
        row.portfolio_id = command.portfolio_id
        row.asset_id = command.asset_id
        row.transaction_type = command.transaction_type
        row.date = command.date
        row.quantity = command.quantity
        row.unit_price = command.unit_price
        row.commission = command.commission
        row.tax = command.tax
        row.note = command.note or None
        session.flush()
        return row

    @staticmethod
    def delete(session: Session, transaction_id: int) -> None:
        row = session.get(Transaction, transaction_id)
        if row is None:
            raise TransactionValidationError(
                TransactionErrorCode.NOT_FOUND, "İşlem bulunamadı."
            )
        with session.no_autoflush:
            TransactionService.validate_ledger(
                session, row.portfolio_id, row.asset_id, exclude_id=row.id
            )
        session.delete(row)
