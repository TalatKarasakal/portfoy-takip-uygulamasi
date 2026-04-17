import yfinance as yf
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from app.utils.logger import prices_logger
from app.utils.cache import price_cache

class BistService:
    def __init__(self):
        self._suffix = ".IS"

    def fetch_current_price(self, symbol: str, force_refresh: bool = False) -> Optional[float]:
        """BIST hisse senedinin anlık fiyatını (ya da son kapanış fiyatını) çeker."""
        if not symbol.endswith(self._suffix):
            symbol = f"{symbol}{self._suffix}"
            
        if not force_refresh:
            cached_price = price_cache.get(f"BIST_{symbol}")
            if cached_price is not None:
                return float(cached_price)

        try:
            prices_logger.debug(f"Fetching yfinance data for {symbol}")
            ticker = yf.Ticker(symbol)
            
            # Anlık fiyatı (veya gün içi en son fiyat)
            history = ticker.history(period="1d")
            if not history.empty:
                latest_price = float(history['Close'].iloc[-1])
                price_cache.set(f"BIST_{symbol}", latest_price)
                return latest_price
            else:
                prices_logger.warning(f"No BIST data returned for {symbol}")
                return None
        except Exception as e:
            prices_logger.error(f"Error fetching BIST {symbol}: {e}")
            #TODO: Yedek kaynak olarak isyatirim.com.tr HTML scraping implemente edilebilir.
            return None

    def fetch_historical_prices(self, symbol: str, period: str = "1y") -> List[Dict[str, Any]]:
        """Verilen periyot için geçmiş fiyatları getirir. (örn. 1mo, 1y, ytd)"""
        if not symbol.endswith(self._suffix):
            symbol = f"{symbol}{self._suffix}"

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
