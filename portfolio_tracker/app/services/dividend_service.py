"""Temettü geçmişi, manuel plan ve verim hesapları."""

from __future__ import annotations

import datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.orm import Session, joinedload

from app.models.dividend_plan import DividendPlan, DividendPlanStatus
from app.models.transaction import Transaction, TransactionType
from app.services.portfolio_service import PortfolioService
from app.services.transaction_service import TransactionCommand, TransactionService

ZERO = Decimal("0")


class DividendService:
    @staticmethod
    def holding_quantity(
        session: Session,
        portfolio_id: int,
        asset_id: int,
        as_of: datetime.date | None = None,
    ) -> Decimal:
        cutoff = as_of or datetime.date.today()
        rows = (
            session.query(Transaction)
            .filter(
                Transaction.portfolio_id == portfolio_id,
                Transaction.asset_id == asset_id,
                Transaction.date <= cutoff,
            )
            .all()
        )
        return PortfolioService.calculate_cost_and_pnl(rows, ZERO, "WAC").remaining_quantity

    @staticmethod
    def add_plan(
        session: Session,
        portfolio_id: int,
        asset_id: int,
        payment_date: datetime.date,
        gross_per_share: Decimal | float | str,
        expected_quantity: Decimal | float | str | None = None,
        note: str = "",
    ) -> DividendPlan:
        per_share = Decimal(str(gross_per_share))
        quantity = (
            Decimal(str(expected_quantity))
            if expected_quantity not in (None, "")
            else None
        )
        if per_share <= ZERO:
            raise ValueError("Hisse başı temettü sıfırdan büyük olmalıdır.")
        if quantity is not None and quantity <= ZERO:
            raise ValueError("Beklenen adet sıfırdan büyük olmalıdır.")
        plan = DividendPlan(
            portfolio_id=portfolio_id,
            asset_id=asset_id,
            payment_date=payment_date,
            gross_per_share=per_share,
            expected_quantity=quantity,
            note=note.strip() or None,
        )
        session.add(plan)
        session.flush()
        return plan

    @staticmethod
    def mark_paid(
        session: Session,
        plan_id: int,
        confirmed_quantity: Decimal | float | str,
        tax: Decimal | float | str = ZERO,
    ) -> Transaction:
        plan = session.get(DividendPlan, plan_id)
        if plan is None:
            raise ValueError("Temettü planı bulunamadı.")
        if plan.status != DividendPlanStatus.PLANNED:
            raise ValueError("Yalnız planlanan temettü ödendi yapılabilir.")
        quantity = Decimal(str(confirmed_quantity))
        available = DividendService.holding_quantity(
            session,
            plan.portfolio_id,
            plan.asset_id,
            min(plan.payment_date, datetime.date.today()),
        )
        if quantity <= ZERO or quantity > available:
            raise ValueError(f"Doğrulanan adet eldeki {available} adedi aşamaz.")
        command = TransactionCommand.from_values(
            portfolio_id=plan.portfolio_id,
            asset_id=plan.asset_id,
            transaction_type=TransactionType.DIVIDEND,
            date=plan.payment_date,
            quantity=quantity,
            unit_price=plan.gross_per_share,
            tax=tax,
            note=plan.note or "Temettü planı ödemesi",
        )
        transaction = TransactionService.create(session, command)
        plan.expected_quantity = quantity
        plan.status = DividendPlanStatus.PAID
        plan.linked_transaction = transaction
        session.flush()
        return transaction

    @staticmethod
    def dashboard(
        session: Session,
        portfolio_id: int | None,
        portfolio_items: list[dict[str, Any]],
    ) -> dict[str, Any]:
        plan_query = session.query(DividendPlan).options(joinedload(DividendPlan.asset))
        tx_query = session.query(Transaction).options(joinedload(Transaction.asset)).filter(
            Transaction.transaction_type == TransactionType.DIVIDEND
        )
        if portfolio_id is not None:
            plan_query = plan_query.filter(DividendPlan.portfolio_id == portfolio_id)
            tx_query = tx_query.filter(Transaction.portfolio_id == portfolio_id)
        plans = plan_query.order_by(DividendPlan.payment_date, DividendPlan.id).all()
        transactions = tx_query.order_by(Transaction.date.desc(), Transaction.id.desc()).all()
        plan_rows = []
        for plan in plans:
            current_quantity = DividendService.holding_quantity(
                session, plan.portfolio_id, plan.asset_id
            )
            plan_rows.append(
                {
                    "id": plan.id,
                    "portfolio_id": plan.portfolio_id,
                    "asset_id": plan.asset_id,
                    "code": plan.asset.code,
                    "payment_date": plan.payment_date,
                    "gross_per_share": float(plan.gross_per_share),
                    "expected_quantity": (
                        float(plan.expected_quantity)
                        if plan.expected_quantity is not None
                        else None
                    ),
                    "current_quantity": float(current_quantity),
                    "status": plan.status.name,
                    "linked_transaction_id": plan.linked_transaction_id,
                    "note": plan.note or "",
                }
            )
        history_rows = [
            {
                "id": row.id,
                "portfolio_id": row.portfolio_id,
                "code": row.asset.code,
                "date": row.date,
                "quantity": float(row.quantity),
                "gross_per_share": float(row.unit_price),
                "net_amount": float(
                    Decimal(str(row.quantity)) * Decimal(str(row.unit_price))
                    - Decimal(str(row.commission))
                    - Decimal(str(row.tax))
                ),
                "note": row.note or "",
            }
            for row in transactions
        ]
        cutoff = datetime.date.today() - datetime.timedelta(days=365)
        last_12_months_net = sum(
            (Decimal(str(row["net_amount"])) for row in history_rows if row["date"] >= cutoff),
            ZERO,
        )
        cost_basis = sum((Decimal(str(item.get("total_cost", 0))) for item in portfolio_items), ZERO)
        market_value = sum(
            (Decimal(str(item.get("current_value", 0))) for item in portfolio_items), ZERO
        )
        return {
            "plans": plan_rows,
            "history": history_rows,
            "last_12_months_net": float(last_12_months_net),
            "yield_on_cost": float(last_12_months_net / cost_basis) if cost_basis > 0 else None,
            "yield_on_market": (
                float(last_12_months_net / market_value) if market_value > 0 else None
            ),
        }
