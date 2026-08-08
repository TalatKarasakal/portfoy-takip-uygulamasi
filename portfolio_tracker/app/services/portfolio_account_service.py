"""Çoklu portföy, nakit defteri ve izleme listesi işlemleri."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any, Optional

from sqlalchemy.orm import Session, joinedload

from app.models.asset import Asset
from app.models.portfolio import CashEntry, CashEntryType, Portfolio, WatchlistItem
from app.models.transaction import Transaction, TransactionType

ZERO = Decimal("0")


class PortfolioAccountError(ValueError):
    pass


class PortfolioAccountService:
    @staticmethod
    def list_portfolios(session: Session) -> list[dict]:
        rows = session.query(Portfolio).order_by(Portfolio.is_default.desc(), Portfolio.name).all()
        return [{"id": row.id, "name": row.name, "is_default": bool(row.is_default)} for row in rows]

    @staticmethod
    def create_portfolio(session: Session, name: str) -> Portfolio:
        clean_name = " ".join(name.split()).strip()
        if not clean_name:
            raise PortfolioAccountError("Portföy adı boş olamaz.")
        if len(clean_name) > 100:
            raise PortfolioAccountError("Portföy adı en fazla 100 karakter olabilir.")
        if session.query(Portfolio).filter(Portfolio.name == clean_name).first():
            raise PortfolioAccountError("Bu adla bir portföy zaten var.")
        row = Portfolio(name=clean_name, is_default=False)
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def delete_portfolio(session: Session, portfolio_id: int) -> None:
        row = session.query(Portfolio).filter_by(id=portfolio_id).first()
        if row is None:
            raise PortfolioAccountError("Portföy bulunamadı.")
        if row.is_default:
            raise PortfolioAccountError("Ana Portföy silinemez.")
        if row.transactions:
            raise PortfolioAccountError("İşlem içeren portföy silinemez.")
        session.delete(row)

    @staticmethod
    def add_cash_entry(
        session: Session,
        portfolio_id: int,
        entry_type: CashEntryType | str,
        entry_date: datetime.date,
        amount: Decimal | float | str,
        note: str = "",
    ) -> CashEntry:
        kind = entry_type if isinstance(entry_type, CashEntryType) else CashEntryType[entry_type]
        value = Decimal(str(amount))
        if entry_date > datetime.date.today():
            raise PortfolioAccountError("Nakit hareketi gelecekte olamaz.")
        if kind == CashEntryType.ADJUSTMENT:
            if value == ZERO:
                raise PortfolioAccountError("Düzeltme tutarı sıfır olamaz.")
        elif value <= ZERO:
            raise PortfolioAccountError("Nakit hareketi tutarı pozitif olmalıdır.")
        if session.get(Portfolio, portfolio_id) is None:
            raise PortfolioAccountError("Portföy bulunamadı.")
        row = CashEntry(
            portfolio_id=portfolio_id,
            entry_type=kind,
            date=entry_date,
            amount=value,
            note=note.strip() or None,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def signed_cash_entry(entry: CashEntry) -> Decimal:
        amount = Decimal(str(entry.amount))
        if entry.entry_type == CashEntryType.WITHDRAWAL:
            return -amount
        return amount

    @staticmethod
    def transaction_cash_flow(transaction: Transaction) -> Decimal:
        quantity = Decimal(str(transaction.quantity))
        price = Decimal(str(transaction.unit_price))
        fees = Decimal(str(transaction.commission)) + Decimal(str(transaction.tax))
        if transaction.transaction_type == TransactionType.BUY:
            return -(quantity * price + fees)
        if transaction.transaction_type in (TransactionType.SELL, TransactionType.DIVIDEND):
            return quantity * price - fees
        return ZERO

    @staticmethod
    def cash_balance(session: Session, portfolio_id: Optional[int]) -> Decimal:
        cash_query = session.query(CashEntry)
        tx_query = session.query(Transaction)
        if portfolio_id is not None:
            cash_query = cash_query.filter(CashEntry.portfolio_id == portfolio_id)
            tx_query = tx_query.filter(Transaction.portfolio_id == portfolio_id)
        cash = sum((PortfolioAccountService.signed_cash_entry(row) for row in cash_query.all()), ZERO)
        cash += sum((PortfolioAccountService.transaction_cash_flow(row) for row in tx_query.all()), ZERO)
        return cash

    @staticmethod
    def external_flow_for_date(
        session: Session, portfolio_id: int, flow_date: datetime.date
    ) -> Decimal:
        rows = (
            session.query(CashEntry)
            .filter(CashEntry.portfolio_id == portfolio_id, CashEntry.date == flow_date)
            .all()
        )
        return sum((PortfolioAccountService.signed_cash_entry(row) for row in rows), ZERO)

    @staticmethod
    def cash_ledger(session: Session, portfolio_id: int) -> list[dict]:
        entries = (
            session.query(CashEntry)
            .filter(CashEntry.portfolio_id == portfolio_id)
            .order_by(CashEntry.date, CashEntry.id)
            .all()
        )
        transactions = (
            session.query(Transaction)
            .options(joinedload(Transaction.asset))
            .filter(Transaction.portfolio_id == portfolio_id)
            .order_by(Transaction.date, Transaction.id)
            .all()
        )
        events: list[dict[str, Any]] = [
            {
                "date": row.date,
                "id": row.id,
                "source": "cash",
                "type": row.entry_type.name,
                "amount": PortfolioAccountService.signed_cash_entry(row),
                "description": row.note or "",
            }
            for row in entries
        ]
        events.extend(
            {
                "date": row.date,
                "id": row.id,
                "source": "transaction",
                "type": row.transaction_type.name,
                "amount": PortfolioAccountService.transaction_cash_flow(row),
                "description": row.asset.code if row.asset else "",
            }
            for row in transactions
        )
        events.sort(key=lambda event: (event["date"], event["source"], event["id"]))
        running = ZERO
        for event in events:
            running += event["amount"]
            event["balance"] = running
        return events

    @staticmethod
    def add_to_watchlist(
        session: Session,
        portfolio_id: int,
        asset_id: int,
        target_price: Decimal | float | str | None = None,
        note: str = "",
    ) -> WatchlistItem:
        existing = (
            session.query(WatchlistItem)
            .filter_by(portfolio_id=portfolio_id, asset_id=asset_id)
            .first()
        )
        if existing:
            return existing
        row = WatchlistItem(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            target_price=Decimal(str(target_price)) if target_price not in (None, "") else None,
            note=note.strip() or None,
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def list_watchlist(session: Session, portfolio_id: Optional[int]) -> list[dict]:
        query = session.query(WatchlistItem).options(joinedload(WatchlistItem.asset))
        if portfolio_id is not None:
            query = query.filter(WatchlistItem.portfolio_id == portfolio_id)
        rows = query.order_by(WatchlistItem.id).all()
        seen = set()
        result = []
        for row in rows:
            if portfolio_id is None and row.asset_id in seen:
                continue
            seen.add(row.asset_id)
            asset: Asset = row.asset
            result.append(
                {
                    "id": row.id,
                    "asset_id": row.asset_id,
                    "code": asset.code,
                    "name": asset.name,
                    "type": asset.asset_type.name,
                    "target_price": float(row.target_price) if row.target_price is not None else None,
                    "note": row.note or "",
                }
            )
        return result
