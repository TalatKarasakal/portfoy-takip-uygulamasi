import datetime
import threading
import time

import pandas as pd

from app.services.pricing_types import DataFreshness
from app.services.refresh_policy import ISTANBUL, RefreshPolicy
from app.services.tefas_service import TefasService
from app.utils.cache import PriceCache


def _at(year, month, day, hour, minute=0):
    return datetime.datetime(year, month, day, hour, minute, tzinfo=ISTANBUL)


def test_cache_honors_per_entry_ttl_with_fake_clock():
    current = [100.0]
    cache = PriceCache(clock=lambda: current[0])
    cache.set("price", 10, ttl=900)
    cache.set("currency", 20, ttl=86400)

    current[0] += 901

    assert cache.get("price") is None
    assert cache.peek("price") == 10
    assert cache.get("currency") == 20


def test_refresh_policy_market_hours_holidays_and_manual_override():
    now = [_at(2026, 8, 7, 10, 0)]  # Cuma
    policy = RefreshPolicy(now=lambda: now[0])
    assert policy.plan().allow_bist_network
    assert not policy.plan().allow_tefas_network

    now[0] = _at(2026, 8, 7, 19, 1)
    assert policy.plan().allow_tefas_network
    policy.mark_tefas_refreshed()
    assert not policy.plan().allow_tefas_network

    now[0] = _at(2026, 8, 8, 12, 0)  # Cumartesi
    assert not policy.plan().allow_bist_network
    assert policy.plan(force_refresh=True).allow_tefas_network

    holiday = RefreshPolicy(
        now=lambda: _at(2026, 8, 7, 11, 0),
        overrides_json='{"holidays":["2026-08-07"]}',
    )
    assert not holiday.plan().allow_bist_network


def test_refresh_policy_honors_half_day_close():
    policy = RefreshPolicy(
        now=lambda: _at(2026, 8, 7, 13, 1),
        overrides_json='{"half_days":{"2026-08-07":"13:00"}}',
    )
    assert not policy.plan().allow_bist_network


def test_tefas_crawler_calls_are_process_serialized(monkeypatch):
    from app.services import tefas_service as module

    monkeypatch.setattr(module, "_LAST_REQUEST_STARTED", 0.0)
    starts = []
    starts_lock = threading.Lock()
    frame = pd.DataFrame(
        [{"date": pd.Timestamp("2026-08-07"), "code": "AFT", "price": 10.0}]
    )

    class FakeCrawler:
        def fetch(self, **_kwargs):
            with starts_lock:
                starts.append(time.monotonic())
            return frame.copy()

    services = [TefasService(), TefasService()]
    for service in services:
        service.crawler = FakeCrawler()
    workers = [
        threading.Thread(
            target=service.fetch_quote,
            args=(code,),
            kwargs={"force_refresh": True},
        )
        for service, code in zip(services, ("AFT", "MAC"), strict=True)
    ]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()

    assert len(starts) == 2
    assert starts[1] - starts[0] >= 0.45


def test_tefas_returns_offline_status_when_schedule_blocks_network(monkeypatch):
    service = TefasService()
    called = False

    def fail_if_called(**_kwargs):
        nonlocal called
        called = True

    monkeypatch.setattr(service.crawler, "fetch", fail_if_called)
    result = service.fetch_quote("ZZZ", allow_network=False)

    assert result.status == DataFreshness.OFFLINE
    assert result.price is None
    assert not called


def test_forced_refresh_is_preserved_while_loader_is_running():
    from app.viewmodels.portfolio_viewmodel import PortfolioViewModel

    assert PortfolioViewModel.merge_force_refresh(False, True)
    assert PortfolioViewModel.merge_force_refresh(True, False)
    assert not PortfolioViewModel.merge_force_refresh(False, False)
