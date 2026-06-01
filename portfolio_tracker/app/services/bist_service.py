import yfinance as yf
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.utils.logger import prices_logger
from app.utils.cache import price_cache


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

        try:
            prices_logger.debug(f"Fetching yfinance quote for {symbol}")
            ticker = yf.Ticker(symbol)
            # Son birkaç işlem günü; sondan bir önceki kapanışı yakalamak için 5 gün.
            history = ticker.history(period="5d")
            if history is not None and not history.empty:
                closes = [float(c) for c in history["Close"].tolist()]
                price = closes[-1]
                prev_close = closes[-2] if len(closes) >= 2 else price
                quote = {"price": price, "prev_close": prev_close}
                price_cache.set(cache_key, quote)
                return quote
            prices_logger.warning(f"No BIST data returned for {symbol}")
            return {"price": None, "prev_close": None}
        except Exception as e:
            prices_logger.error(f"Error fetching BIST {symbol}: {e}")
            # TODO: Yedek kaynak olarak isyatirim.com.tr HTML scraping implemente edilebilir.
            return {"price": None, "prev_close": None}

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
                return records
            return []
        except Exception as e:
            prices_logger.error(f"Historical fetching error for BIST {symbol}: {e}")
            return []
