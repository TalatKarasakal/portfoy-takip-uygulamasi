import datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.base import Base
from app.models.asset import Asset, AssetType
from app.models.portfolio import Portfolio
from app.models.transaction import TransactionType
from app.services.portfolio_service import PortfolioCalculationError, PortfolioService
from app.services.transaction_service import (
    TransactionCommand,
    TransactionErrorCode,
    TransactionService,
    TransactionValidationError,
)


@pytest.fixture
def ledger():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    portfolio = Portfolio(id=1, name="Ana Portföy", is_default=True)
    asset = Asset(code="THYAO", name="THYAO", asset_type=AssetType.BIST)
    session.add_all([portfolio, asset])
    session.commit()
    yield session, asset
    session.close()
    engine.dispose()


def _command(asset_id, kind, quantity, price, tx_date="2024-01-02"):
    return TransactionCommand.from_values(
        portfolio_id=1,
        asset_id=asset_id,
        transaction_type=kind,
        date=tx_date,
        quantity=quantity,
        unit_price=price,
    )


def test_create_uses_six_decimal_precision(ledger):
    session, asset = ledger
    row = TransactionService.create(
        session, _command(asset.id, "BUY", "1.1234564", "10.9876544")
    )
    session.commit()
    assert row.quantity == Decimal("1.123456")
    assert row.unit_price == Decimal("10.987654")


def test_all_invalid_base_values_are_rejected(ledger):
    session, asset = ledger
    invalid_commands = [
        _command(asset.id, "BUY", 0, 10),
        _command(asset.id, "BUY", 1, 0),
        TransactionCommand.from_values(
            portfolio_id=1,
            asset_id=asset.id,
            transaction_type="BUY",
            date=datetime.date.today() + datetime.timedelta(days=1),
            quantity=1,
            unit_price=1,
        ),
        TransactionCommand.from_values(
            portfolio_id=1,
            asset_id=asset.id,
            transaction_type="SPLIT",
            date=datetime.date.today(),
            quantity=1,
            unit_price=2,
        ),
    ]
    for command in invalid_commands:
        with pytest.raises(TransactionValidationError):
            TransactionService.create(session, command)
        session.rollback()


def test_oversell_is_rejected_with_stable_error_code(ledger):
    session, asset = ledger
    TransactionService.create(session, _command(asset.id, "BUY", 10, 100))
    session.commit()

    with pytest.raises(TransactionValidationError) as error:
        TransactionService.create(session, _command(asset.id, "SELL", 15, 120))
    assert error.value.code == TransactionErrorCode.OVERSELL


def test_update_and_delete_validate_entire_historical_ledger(ledger):
    session, asset = ledger
    buy = TransactionService.create(session, _command(asset.id, "BUY", 10, 100))
    sell = TransactionService.create(
        session, _command(asset.id, "SELL", 8, 120, "2024-01-03")
    )
    session.commit()

    with pytest.raises(TransactionValidationError) as update_error:
        TransactionService.update(session, buy.id, _command(asset.id, "BUY", 5, 100))
    assert update_error.value.code == TransactionErrorCode.OVERSELL
    session.rollback()

    with pytest.raises(TransactionValidationError) as delete_error:
        TransactionService.delete(session, buy.id)
    assert delete_error.value.code == TransactionErrorCode.OVERSELL
    session.rollback()
    assert session.get(type(sell), sell.id) is not None


def test_same_day_order_is_deterministic_and_split_affects_later_sale(ledger):
    session, asset = ledger
    TransactionService.create(session, _command(asset.id, "BUY", 10, 100))
    TransactionService.create(session, _command(asset.id, "SPLIT", 0, 2))
    sale = TransactionService.create(session, _command(asset.id, "SELL", 20, 60))
    session.commit()
    assert sale.id is not None


@pytest.mark.parametrize("method", ["WAC", "FIFO", "LIFO"])
def test_cost_methods_refuse_legacy_oversell(ledger, method):
    session, asset = ledger
    buy = TransactionService.create(session, _command(asset.id, "BUY", 10, 100))
    session.commit()
    # Geçmişte doğrulama olmadan yazılmış bir satırı taklit et.
    from app.models.transaction import Transaction

    bad_sell = Transaction(
        portfolio_id=1,
        asset_id=asset.id,
        transaction_type=TransactionType.SELL,
        date=datetime.date(2024, 1, 3),
        quantity=15,
        unit_price=120,
        commission=0,
        tax=0,
    )
    with pytest.raises(PortfolioCalculationError, match="aşıyor"):
        PortfolioService.calculate_cost_and_pnl([buy, bad_sell], 130, method)
