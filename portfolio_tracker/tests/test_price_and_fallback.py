import datetime

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.base import Base
from app.models.asset import Asset, AssetType
from app.models.price_history import PriceHistory
from app.services.price_history_service import PriceHistoryService


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    s = sessionmaker(bind=engine)()
    yield s
    s.close()


def _add_asset(session):
    a = Asset(code="THYAO", name="THY", asset_type=AssetType.BIST)
    session.add(a)
    session.commit()
    return a.id


def test_price_history_upsert_and_last_close(session):
    aid = _add_asset(session)
    d = datetime.date(2024, 1, 1)
    PriceHistoryService.record_close(session, aid, 100.0, date=d)
    PriceHistoryService.record_close(session, aid, 110.0, date=d)  # aynı gün -> upsert
    rows = session.query(PriceHistory).all()
    assert len(rows) == 1
    assert float(rows[0].close_price) == 110.0

    PriceHistoryService.record_close(session, aid, 120.0, date=datetime.date(2024, 1, 2))
    assert PriceHistoryService.last_close(session, aid) == 120.0


def test_record_close_ignores_nonpositive(session):
    aid = _add_asset(session)
    PriceHistoryService.record_close(session, aid, 0.0)
    PriceHistoryService.record_close(session, aid, -5.0)
    assert session.query(PriceHistory).count() == 0
    assert PriceHistoryService.last_close(session, aid) is None


def test_bist_falls_back_to_isyatirim(monkeypatch):
    from app.services import bist_service as bist_mod
    from app.services.bist_service import BistService
    from app.utils.cache import price_cache
    price_cache.clear()

    # yfinance boş döner gibi davransın
    class _EmptyHist:
        empty = True

    class _FakeTicker:
        def __init__(self, *a, **k):
            pass

        def history(self, *a, **k):
            return _EmptyHist()

    monkeypatch.setattr(bist_mod.yf, "Ticker", _FakeTicker)
    # İş Yatırım sabit bir kotasyon döndürsün
    monkeypatch.setattr(
        bist_mod.IsYatirimService, "fetch_quote",
        staticmethod(lambda code: {"price": 42.0, "prev_close": 40.0}),
    )

    svc = BistService()
    quote = svc.fetch_quote("THYAO", force_refresh=True)
    assert quote["price"] == 42.0
    assert quote["prev_close"] == 40.0
