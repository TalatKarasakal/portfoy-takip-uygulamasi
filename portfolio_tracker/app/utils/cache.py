"""Farklı veri sınıfları için süreli ve test edilebilir bellek önbelleği."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any


class PriceCache:
    DEFAULT_TTL = 15 * 60
    PRICE_TTL = 15 * 60
    CURRENCY_TTL = 24 * 60 * 60
    BENCHMARK_TTL = 6 * 60 * 60
    FUND_NAME_TTL = 7 * 24 * 60 * 60

    def __init__(self, clock: Callable[[], float] | None = None) -> None:
        self._clock = clock or time.monotonic
        self._cache: dict[str, tuple[float, float, Any]] = {}

    def get(self, key: str) -> Any | None:
        entry = self._cache.get(key)
        if entry is None:
            return None
        timestamp, ttl, value = entry
        if self._clock() - timestamp < ttl:
            return value
        return None

    def peek(self, key: str) -> Any | None:
        """Süresi dolmuş olsa da son bilinen değeri çevrimdışı kullanım için döndürür."""
        entry = self._cache.get(key)
        return entry[2] if entry is not None else None

    def set(self, key: str, value: Any, ttl: float | None = None) -> None:
        self._cache[key] = (self._clock(), ttl or self.DEFAULT_TTL, value)

    def clear(self) -> None:
        self._cache.clear()


price_cache = PriceCache()
