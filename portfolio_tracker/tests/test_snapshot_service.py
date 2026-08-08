import datetime

import pytest
from conftest import dispose_session_engine
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401  (tüm modelleri registry'ye kaydeder)
from app.database.base import Base
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.services.snapshot_service import SnapshotService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    dispose_session_engine(s)


def test_record_snapshot_upserts_same_day(session):
    d = datetime.date(2024, 1, 1)
    SnapshotService.record_snapshot(session, 1000, 900, 100, 50, snapshot_date=d)
    # Aynı gün ikinci kayıt üzerine yazmalı, yeni satır eklememeli
    SnapshotService.record_snapshot(session, 1100, 950, 150, 55, snapshot_date=d)

    rows = session.query(PortfolioSnapshot).all()
    assert len(rows) == 1
    assert float(rows[0].total_value_try) == 1100
    assert float(rows[0].total_cost_try) == 950
    assert float(rows[0].total_value_usd) == 55


def test_get_history_sorted_and_typed(session):
    SnapshotService.record_snapshot(session, 2, 2, 0, 0, snapshot_date=datetime.date(2024, 1, 2))
    SnapshotService.record_snapshot(session, 1, 1, 0, 0, snapshot_date=datetime.date(2024, 1, 1))
    hist = SnapshotService.get_history(session)
    assert [h["total_value_try"] for h in hist] == [1.0, 2.0]
    assert isinstance(hist[0]["date"], datetime.date)


def test_get_history_days_filter(session):
    today = datetime.date.today()
    SnapshotService.record_snapshot(session, 1, 1, 0, 0, snapshot_date=today - datetime.timedelta(days=100))
    SnapshotService.record_snapshot(session, 2, 1, 0, 0, snapshot_date=today - datetime.timedelta(days=5))
    hist = SnapshotService.get_history(session, days=30)
    assert len(hist) == 1
    assert hist[0]["total_value_try"] == 2.0
