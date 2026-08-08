import datetime
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.base import Base
from app.models.asset import Asset, AssetType
from app.models.dividend_plan import DividendPlanStatus
from app.models.portfolio import Portfolio
from app.models.transaction import Transaction, TransactionType
from app.services.dividend_service import DividendService


def _session(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'dividends.db'}")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)(), engine


def test_mark_paid_creates_linked_dividend_atomically(tmp_path):
    session, engine = _session(tmp_path)
    portfolio = Portfolio(name="Ana", is_default=True)
    asset = Asset(code="THYAO", name="THY", asset_type=AssetType.BIST)
    session.add_all([portfolio, asset])
    session.flush()
    session.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            date=datetime.date(2024, 1, 1),
            quantity=Decimal("10"),
            unit_price=Decimal("100"),
            commission=Decimal("0"),
            tax=Decimal("0"),
        )
    )
    plan = DividendService.add_plan(
        session,
        portfolio.id,
        asset.id,
        datetime.date(2024, 6, 1),
        "2.5",
    )
    session.commit()

    transaction = DividendService.mark_paid(session, plan.id, "10")
    session.commit()

    session.refresh(plan)
    assert plan.status == DividendPlanStatus.PAID
    assert plan.linked_transaction_id == transaction.id
    assert transaction.transaction_type == TransactionType.DIVIDEND
    assert transaction.quantity == Decimal("10.000000")
    session.close()
    engine.dispose()


def test_mark_paid_rejects_quantity_above_holding(tmp_path):
    session, engine = _session(tmp_path)
    portfolio = Portfolio(name="Ana", is_default=True)
    asset = Asset(code="ASELS", name="ASELS", asset_type=AssetType.BIST)
    session.add_all([portfolio, asset])
    session.flush()
    session.add(
        Transaction(
            portfolio_id=portfolio.id,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            date=datetime.date(2024, 1, 1),
            quantity=Decimal("5"),
            unit_price=Decimal("50"),
            commission=Decimal("0"),
            tax=Decimal("0"),
        )
    )
    plan = DividendService.add_plan(
        session, portfolio.id, asset.id, datetime.date(2024, 6, 1), "1"
    )
    session.commit()

    try:
        DividendService.mark_paid(session, plan.id, "6")
    except ValueError as exc:
        assert "aşamaz" in str(exc)
    else:
        raise AssertionError("Fazla temettü adedi reddedilmeliydi")
    assert session.query(Transaction).filter_by(transaction_type=TransactionType.DIVIDEND).count() == 0
    session.close()
    engine.dispose()
