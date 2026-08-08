"""Fiyat ve benchmark servisleri için tipli sonuç nesneleri."""

from __future__ import annotations

import datetime
from dataclasses import dataclass, replace
from enum import StrEnum
from typing import Any


class DataFreshness(StrEnum):
    LIVE = "canlı"
    CACHE = "önbellek"
    STALE = "eski"
    OFFLINE = "çevrimdışı"


@dataclass(frozen=True)
class QuoteResult:
    price: float | None
    prev_close: float | None
    source: str
    price_date: datetime.date | None
    fetched_at: datetime.datetime
    status: DataFreshness
    error: str | None = None

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def with_status(self, status: DataFreshness, error: str | None = None) -> QuoteResult:
        return replace(self, status=status, error=error if error is not None else self.error)


@dataclass(frozen=True)
class BenchmarkResult:
    series: dict[str, list[tuple[datetime.date, float]]]
    fetched_at: datetime.datetime
    status: DataFreshness
    error: str | None = None

    def items(self):
        return self.series.items()

    def __bool__(self) -> bool:
        return bool(self.series)
