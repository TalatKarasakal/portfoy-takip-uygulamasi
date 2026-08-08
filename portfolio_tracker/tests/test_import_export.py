import datetime
from decimal import Decimal

import pandas as pd
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.base import Base
from app.models.asset import Asset, AssetType
from app.models.dividend_plan import DividendPlan
from app.models.import_batch import ImportBatch, ImportBatchStatus
from app.models.portfolio import CashEntryType, Portfolio
from app.models.transaction import Transaction, TransactionType
from app.services.dividend_service import DividendService
from app.services.import_export_service import (
    ImportExportService,
    ImportRowStatus,
    ImportValidationError,
)
from app.services.portfolio_account_service import PortfolioAccountService
from app.services.transaction_service import TransactionCommand, TransactionService


@pytest.fixture
def db_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    session.add(Portfolio(id=1, name="Ana Portföy", is_default=True))
    session.commit()
    yield session
    session.close()
    engine.dispose()


def _add_transaction(session, asset, kind, day, quantity, price, note=""):
    return TransactionService.create(
        session,
        TransactionCommand.from_values(
            portfolio_id=1,
            asset_id=asset.id,
            transaction_type=kind,
            date=day,
            quantity=quantity,
            unit_price=price,
            commission="1.123456" if kind != "SPLIT" else 0,
            tax="0.123456" if kind != "SPLIT" else 0,
            note=note,
        ),
    )


def test_real_excel_round_trip_preserves_all_entities(db_session, tmp_path):
    asset = Asset(code="THYAO", name="Türk Hava Yolları", asset_type=AssetType.BIST)
    db_session.add(asset)
    db_session.flush()
    _add_transaction(db_session, asset, "BUY", "2024-01-02", "10.123456", "100.123456")
    _add_transaction(db_session, asset, "SPLIT", "2024-01-03", 0, 2)
    _add_transaction(db_session, asset, "SELL", "2024-01-04", 5, 120)
    _add_transaction(db_session, asset, "DIVIDEND", "2024-01-05", 15, 2, "Net temettü")
    PortfolioAccountService.add_cash_entry(
        db_session, 1, CashEntryType.DEPOSIT, datetime.date(2024, 1, 1), 2000, "Başlangıç"
    )
    PortfolioAccountService.add_to_watchlist(db_session, 1, asset.id, "150.123456", "Hedef")
    DividendService.add_plan(
        db_session, 1, asset.id, datetime.date(2024, 2, 1), "3.123456", "15", "Plan"
    )
    db_session.commit()

    workbook = tmp_path / "roundtrip.xlsx"
    ImportExportService.export_excel(db_session, str(workbook), portfolio_id=1)

    target_engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(target_engine)
    target = sessionmaker(bind=target_engine)()
    target.add(Portfolio(id=1, name="Ana Portföy", is_default=True))
    target.commit()
    preview = ImportExportService.preview_excel(target, str(workbook), 1)
    assert not preview.has_errors
    assert {row.entity for row in preview.rows} == {
        "transaction",
        "cash",
        "watchlist",
        "dividend_plan",
    }
    result = ImportExportService.apply_preview(target, preview)
    target.commit()

    assert result.imported_count == 7
    imported = target.query(Transaction).order_by(Transaction.id).all()
    assert [row.transaction_type for row in imported] == [
        TransactionType.BUY,
        TransactionType.SPLIT,
        TransactionType.SELL,
        TransactionType.DIVIDEND,
    ]
    assert imported[0].quantity == Decimal("10.123456")
    assert imported[0].unit_price == Decimal("100.123456")
    assert imported[-1].note == "Net temettü"
    assert target.query(ImportBatch).one().status == ImportBatchStatus.APPLIED
    assert len(PortfolioAccountService.list_watchlist(target, 1)) == 1
    assert target.query(DividendPlan).one().gross_per_share == Decimal("3.123456")
    target.close()
    target_engine.dispose()


def test_one_bad_row_blocks_entire_file(db_session, tmp_path):
    workbook = tmp_path / "bad.xlsx"
    pd.DataFrame(
        [
            {
                "Tarih": "2024-01-01",
                "Varlık Kodu": "THYAO",
                "İşlem Türü": "BUY",
                "Adet": 10,
                "Birim Fiyat": 100,
            },
            {
                "Tarih": "not-a-date",
                "Varlık Kodu": "AFT",
                "İşlem Türü": "BUY",
                "Adet": 5,
                "Birim Fiyat": 20,
            },
        ]
    ).to_excel(workbook, sheet_name="İşlemler", index=False)

    preview = ImportExportService.preview_excel(db_session, str(workbook), 1)
    assert preview.has_errors
    assert [row.status for row in preview.rows] == [ImportRowStatus.WARNING, ImportRowStatus.ERROR]
    with pytest.raises(ImportValidationError, match="Hatalı"):
        ImportExportService.apply_preview(db_session, preview)
    db_session.rollback()
    assert db_session.query(Transaction).count() == 0
    assert db_session.query(Asset).count() == 0


def test_duplicates_are_unselected_but_user_can_include_them(db_session, tmp_path):
    workbook = tmp_path / "duplicate.xlsx"
    pd.DataFrame(
        [{"Tarih": "2024-01-01", "Kod": "THYAO", "Tür": "BUY", "Adet": 1, "Birim Fiyat": 10}]
    ).to_excel(workbook, index=False)
    first = ImportExportService.preview_excel(db_session, str(workbook), 1)
    ImportExportService.apply_preview(db_session, first)
    db_session.commit()

    duplicate = ImportExportService.preview_excel(db_session, str(workbook), 1)
    assert duplicate.rows[0].status == ImportRowStatus.DUPLICATE
    assert duplicate.selected_count == 0
    ImportExportService.apply_preview(db_session, duplicate, selected_rows=[0])
    db_session.commit()
    assert db_session.query(Transaction).count() == 2


def test_undo_refuses_when_later_sale_depends_on_import(db_session, tmp_path):
    workbook = tmp_path / "buy.xlsx"
    pd.DataFrame(
        [{"Tarih": "2024-01-01", "Kod": "THYAO", "Tür": "BUY", "Adet": 10, "Birim Fiyat": 10}]
    ).to_excel(workbook, index=False)
    preview = ImportExportService.preview_excel(db_session, str(workbook), 1)
    ImportExportService.apply_preview(db_session, preview)
    db_session.commit()
    asset = db_session.query(Asset).filter_by(code="THYAO").one()
    TransactionService.create(
        db_session,
        TransactionCommand.from_values(
            portfolio_id=1,
            asset_id=asset.id,
            transaction_type="SELL",
            date="2024-01-02",
            quantity=5,
            unit_price=11,
        ),
    )
    db_session.commit()

    with pytest.raises(Exception, match="aşıyor"):
        ImportExportService.undo_last_import(db_session, 1)
    db_session.rollback()
    assert db_session.query(Transaction).count() == 2


def test_undo_removes_last_batch_when_safe(db_session, tmp_path):
    workbook = tmp_path / "safe.xlsx"
    pd.DataFrame(
        [{"Tarih": "2024-01-01", "Kod": "AFT", "Tür": "BUY", "Adet": 2, "Birim Fiyat": 20}]
    ).to_excel(workbook, index=False)
    preview = ImportExportService.preview_excel(db_session, str(workbook), 1)
    ImportExportService.apply_preview(db_session, preview)
    db_session.commit()

    assert ImportExportService.undo_last_import(db_session, 1) == 1
    db_session.commit()
    assert db_session.query(Transaction).count() == 0
    assert db_session.query(ImportBatch).one().status == ImportBatchStatus.UNDONE


def test_percentage_import_rolls_back_if_one_price_is_missing(db_session, tmp_path, monkeypatch):
    from app.services.bist_service import BistService

    workbook = tmp_path / "percentage.xlsx"
    pd.DataFrame({"Kod": ["THYAO", "TUPRS"], "Yüzde": [50, 50]}).to_excel(
        workbook, index=False
    )
    monkeypatch.setattr(
        BistService,
        "fetch_current_price",
        lambda _self, code, force_refresh=False: 10 if code == "THYAO" else None,
    )

    assert not ImportExportService.import_percentage(db_session, str(workbook), 1000, 1)
    assert db_session.query(Transaction).count() == 0
    assert db_session.query(Asset).count() == 0
