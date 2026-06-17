"""Karşılaştırma (benchmark) serileri.

Portföy getirisini kıyaslamak için BIST 100, USD/TRY ve gram altın (TRY)
tarihsel serilerini yfinance üzerinden çeker. Her seri (tarih, değer) listesi
olarak döner; normalize etme (100'e rebase) çağıran tarafta yapılır.

Not: TÜFE/enflasyon serisi ücretsiz ve güvenilir bir API olmadığından dahil
edilmemiştir.
"""

import datetime
from typing import Dict, List, Tuple

import yfinance as yf

from app.utils.cache import price_cache
from app.utils.logger import prices_logger

# Bir ons altın = 31.1034768 gram
OUNCE_TO_GRAM = 31.1034768

Series = List[Tuple[datetime.date, float]]


class BenchmarkService:
    @staticmethod
    def _history_closes(ticker: str, start: datetime.date, end: datetime.date) -> Series:
        try:
            data = yf.Ticker(ticker).history(
                start=start.strftime("%Y-%m-%d"),
                end=(end + datetime.timedelta(days=1)).strftime("%Y-%m-%d"),
            )
            if data is None or data.empty:
                return []
            return [(idx.date(), float(row["Close"])) for idx, row in data.iterrows()]
        except Exception as e:
            prices_logger.error(f"Benchmark {ticker} çekilemedi: {e}")
            return []

    @staticmethod
    def fetch_series(start: datetime.date, end: datetime.date,
                     force_refresh: bool = False) -> Dict[str, Series]:
        """BIST 100, USD/TRY ve gram altın (TRY) serilerini döndürür.

        Sonuç 6 saat cache'lenir (benchmark verisi sık değişmez).
        """
        cache_key = f"BENCHMARK_{start.isoformat()}_{end.isoformat()}"
        if not force_refresh:
            cached = price_cache.get(cache_key)
            if cached is not None:
                return cached

        result: Dict[str, Series] = {}

        bist = BenchmarkService._history_closes("XU100.IS", start, end)
        if bist:
            result["BIST 100"] = bist

        usdtry = BenchmarkService._history_closes("USDTRY=X", start, end)
        if usdtry:
            result["USD/TRY"] = usdtry

        # Gram altın (TRY) = (ons altın USD / 31.1035) * USD/TRY
        gold_usd = BenchmarkService._history_closes("GC=F", start, end)
        if gold_usd and usdtry:
            usd_map = {d: v for d, v in usdtry}
            gram_series: Series = []
            for d, oz_usd in gold_usd:
                rate = usd_map.get(d)
                if rate is None:
                    # En yakın önceki kuru bul
                    candidates = [r for dd, r in usdtry if dd <= d]
                    if not candidates:
                        continue
                    rate = candidates[-1]
                gram_series.append((d, (oz_usd / OUNCE_TO_GRAM) * rate))
            if gram_series:
                result["Gram Altın"] = gram_series

        price_cache.set(cache_key, result)
        return result
