import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.base import Base
from app.models.asset import Asset, AssetType
from app.models.portfolio import CashEntryType, Portfolio
from app.models.transaction import Transaction, TransactionType
from app.services.portfolio_account_service import (
    PortfolioAccountError,
    PortfolioAccountService,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    db = sessionmaker(bind=engine)()
    db.add(Portfolio(id=1, name="Ana Portföy", is_default=True))
    db.commit()
    yield db
    db.close()
    engine.dispose()


def test_cash_balance_combines_external_and_transaction_flows(session):
    asset = Asset(code="THYAO", name="THYAO", asset_type=AssetType.BIST)
    session.add(asset)
    session.flush()
    PortfolioAccountService.add_cash_entry(
        session, 1, CashEntryType.DEPOSIT, datetime.date.today(), Decimal("1500")
    )
    session.add(
        Transaction(
            portfolio_id=1,
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            date=datetime.date.today(),
            quantity=Decimal("10"),
            unit_price=Decimal("100"),
            commission=Decimal("2"),
            tax=Decimal("0"),
        )
    )
    session.flush()

    assert PortfolioAccountService.cash_balance(session, 1) == Decimal("498")


def test_portfolio_names_are_unique_and_default_cannot_be_deleted(session):
    created = PortfolioAccountService.create_portfolio(session, "Uzun Vade")
    assert created.name == "Uzun Vade"
    with pytest.raises(PortfolioAccountError, match="zaten"):
        PortfolioAccountService.create_portfolio(session, "Uzun   Vade")
    with pytest.raises(PortfolioAccountError, match="Ana Portföy"):
        PortfolioAccountService.delete_portfolio(session, 1)


def test_watchlist_is_portfolio_scoped_and_consolidated_is_unique(session):
    second = PortfolioAccountService.create_portfolio(session, "İkinci")
    asset = Asset(code="AFT", name="AFT", asset_type=AssetType.TEFAS)
    session.add(asset)
    session.flush()
    PortfolioAccountService.add_to_watchlist(session, 1, asset.id, "12.345678")
    PortfolioAccountService.add_to_watchlist(session, second.id, asset.id)

    assert len(PortfolioAccountService.list_watchlist(session, 1)) == 1
    assert len(PortfolioAccountService.list_watchlist(session, None)) == 1


def test_cash_entry_validation(session):
    with pytest.raises(PortfolioAccountError, match="pozitif"):
        PortfolioAccountService.add_cash_entry(
            session, 1, CashEntryType.DEPOSIT, datetime.date.today(), Decimal("0")
        )
    with pytest.raises(PortfolioAccountError, match="gelecekte"):
        PortfolioAccountService.add_cash_entry(
            session,
            1,
            CashEntryType.DEPOSIT,
            datetime.date.today() + datetime.timedelta(days=1),
            Decimal("1"),
        )
