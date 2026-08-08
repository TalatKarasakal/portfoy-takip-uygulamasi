"""BIST ve TEFAS otomatik yenileme saatlerini belirleyen yerel politika."""

from __future__ import annotations

import datetime
import json
import threading
from collections.abc import Callable
from dataclasses import dataclass
from zoneinfo import ZoneInfo

ISTANBUL = ZoneInfo("Europe/Istanbul")


@dataclass(frozen=True)
class RefreshPlan:
    allow_bist_network: bool
    allow_tefas_network: bool
    forced: bool


class RefreshPolicy:
    """Manuel çağrıyı serbest bırakır; otomatik çağrıyı piyasa saatleriyle sınırlar."""

    def __init__(
        self,
        now: Callable[[], datetime.datetime] | None = None,
        overrides_json: str = "",
    ) -> None:
        self._now = now or (lambda: datetime.datetime.now(ISTANBUL))
        self._lock = threading.Lock()
        self._last_tefas_refresh: datetime.date | None = None
        self.configure(overrides_json)

    def configure(self, overrides_json: str) -> None:
        try:
            parsed = json.loads(overrides_json) if overrides_json else {}
        except (TypeError, ValueError):
            parsed = {}
        self._holidays = set(parsed.get("holidays", []))
        self._half_days = dict(parsed.get("half_days", {}))

    def plan(self, force_refresh: bool = False) -> RefreshPlan:
        if force_refresh:
            return RefreshPlan(True, True, True)
        now = self._now().astimezone(ISTANBUL)
        date_key = now.date().isoformat()
        is_business_day = now.weekday() < 5 and date_key not in self._holidays
        close_text = self._half_days.get(date_key, "18:10")
        try:
            close_time = datetime.time.fromisoformat(close_text)
        except ValueError:
            close_time = datetime.time(18, 10)
        bist_open = is_business_day and datetime.time(10, 0) <= now.time() <= close_time
        with self._lock:
            tefas_due = (
                is_business_day
                and now.time() >= datetime.time(19, 0)
                and self._last_tefas_refresh != now.date()
            )
        return RefreshPlan(bist_open, tefas_due, False)

    def mark_tefas_refreshed(self) -> None:
        with self._lock:
            self._last_tefas_refresh = self._now().astimezone(ISTANBUL).date()
