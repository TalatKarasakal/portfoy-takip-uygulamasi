import datetime as _dt
from typing import Any, Dict, List, Optional

import yfinance as yf

from app.services.isyatirim_service import IsYatirimService
from app.utils.cache import price_cache
from app.utils.logger import prices_logger


class BistService:
    def __init__(self):
        self._suffix = ".IS"

    def _normalize(self, symbol: str) -> str:
        if not symbol.endswith(self._suffix):
            return f"{symbol}{self._suffix}"
        return symbol

    def fetch_quote(self, symbol: str, force_refresh: bool = False) -> Dict[str, Optional[float]]:
        """BIST hissesinin güncel fiyatını ve bir önceki kapanışını döndürür.

        Returns:
            {"price": float | None, "prev_close": float | None}
            Tek bir ağ isteğiyle her ikisi de alınır ve birlikte cache'lenir.
        """
        symbol = self._normalize(symbol)
        cache_key = f"BIST_QUOTE_{symbol}"

        if not force_refresh:
            cached = price_cache.get(cache_key)
            if cached is not None:
                return cached

        quote = {"price": None, "prev_close": None}
        try:
            prices_logger.debug(f"Fetching yfinance quote for {symbol}")
            ticker = yf.Ticker(symbol)
            # Son birkaç işlem günü; sondan bir önceki kapanışı yakalamak için 5 gün.
            history = ticker.history(period="5d")
            if history is not None and not history.empty:
                closes = [float(c) for c in history["Close"].tolist()]
                quote = {"price": closes[-1], "prev_close": closes[-2] if len(closes) >= 2 else closes[-1]}
        except Exception as e:
            prices_logger.error(f"Error fetching BIST {symbol} (yfinance): {e}")

        # yfinance başarısızsa İş Yatırım'a düş
        if quote.get("price") is None:
            prices_logger.debug(f"yfinance boş; İş Yatırım'a düşülüyor: {symbol}")
            quote = IsYatirimService.fetch_quote(symbol)

        if quote.get("price") is not None:
            price_cache.set(cache_key, quote)
        else:
            prices_logger.warning(f"No BIST data returned for {symbol} (yfinance + İş Yatırım)")
        return quote

    def fetch_current_price(self, symbol: str, force_refresh: bool = False) -> Optional[float]:
        """BIST hisse senedinin anlık fiyatını (ya da son kapanış fiyatını) çeker."""
        return self.fetch_quote(symbol, force_refresh).get("price")

    def fetch_historical_prices(self, symbol: str, period: str = "1y") -> List[Dict[str, Any]]:
        """Verilen periyot için geçmiş fiyatları getirir. (örn. 1mo, 1y, ytd)"""
        symbol = self._normalize(symbol)

        try:
            ticker = yf.Ticker(symbol)
            history = ticker.history(period=period)

            if not history.empty:
                records = []
                for index, row in history.iterrows():
                    records.append({
                        "date": index.date(),
                        "close_price": float(row["Close"])
                    })
                if records:
                    return records
        except Exception as e:
            prices_logger.error(f"Historical fetching error for BIST {symbol} (yfinance): {e}")

        # yfinance boş döndüyse İş Yatırım'a düş
        days = self._period_to_days(period)
        end = _dt.date.today()
        start = end - _dt.timedelta(days=days)
        return IsYatirimService.fetch_historical_prices(symbol, start, end)

    @staticmethod
    def _period_to_days(period: str) -> int:
        mapping = {"1mo": 31, "3mo": 93, "6mo": 186, "1y": 366, "2y": 732, "ytd": 366, "5d": 7}
        return mapping.get(period, 366)
