import yfinance as yf
import requests
import re
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
                prices_logger.warning(f"No BIST data returned for {symbol} from yfinance. Attempting fallback.")
                fallback_price = self._scrape_isyatirim_price(symbol)
                if fallback_price is not None:
                    price_cache.set(f"BIST_{symbol}", fallback_price)
                    return fallback_price
                return None
        except Exception as e:
            prices_logger.error(f"Error fetching BIST {symbol} from yfinance: {e}. Attempting fallback.")
            fallback_price = self._scrape_isyatirim_price(symbol)
            if fallback_price is not None:
                price_cache.set(f"BIST_{symbol}", fallback_price)
                return fallback_price
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

    def _scrape_isyatirim_price(self, symbol: str) -> Optional[float]:
        """isyatirim.com.tr üzerinden güncel fiyatı çeker (yfinance yedeği)."""
        try:
            # Remove .IS suffix if exists
            clean_symbol = symbol.replace(self._suffix, "") if symbol.endswith(self._suffix) else symbol

            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            url = "https://www.isyatirim.com.tr/tr-tr/analiz/hisse/Sayfalar/default.aspx"
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()
            html = response.text

            # Regex to find the row for the specific symbol and extract the price from the next cell
            # Example HTML chunk:
            # <a href="/tr-tr/analiz/hisse/Sayfalar/sirket-karti.aspx?hisse=THYAO">\r\n                                        THYAO\r\n                                    </a>​\r\n                                </td>\r\n                                <td class="text-right">308,25</td>

            pattern = re.compile(f'{clean_symbol}\\s*</a>.*?<td class="text-right">([0-9.,]+)</td>', re.DOTALL | re.IGNORECASE)
            match = pattern.search(html)

            if match:
                price_str = match.group(1).strip()
                # Is Yatirim format might be "1.234,56" or "308,25".
                # Strip dots used as thousands separator, replace comma with dot
                price_str = price_str.replace('.', '').replace(',', '.')
                return float(price_str)
            else:
                prices_logger.warning(f"Could not find HTML price for {clean_symbol} on isyatirim.com.tr")
                return None

        except Exception as e:
            prices_logger.error(f"HTML scraping failed for {symbol}: {e}")
            return None
