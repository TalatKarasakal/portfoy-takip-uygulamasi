import time
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from tefas import Crawler
from app.utils.logger import prices_logger
from app.utils.cache import price_cache

class TefasService:
    def __init__(self):
        self.crawler = Crawler()
        self.max_retries = 3

    def fetch_fund_name(self, fund_code: str) -> Optional[str]:
        """Fonun resmî tam adını (title) TEFAS'tan çeker.

        Sonuç uzun süre geçerli olduğundan kalıcı kabul edilir ve in-memory
        cache'lenir. Hata durumunda None döner.
        """
        cache_key = f"TEFAS_NAME_{fund_code}"
        cached = price_cache.get(cache_key)
        if cached is not None:
            return cached or None

        end_date = datetime.now()
        start_date = end_date - timedelta(days=10)
        try:
            time.sleep(0.5)  # rate limit önlemi
            df = self.crawler.fetch(
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                name=fund_code,
                columns=["date", "code", "title"],
            )
            if df is not None and not df.empty and "title" in df.columns:
                title = str(df.iloc[-1]["title"]).strip()
                if title and title.lower() != "nan":
                    price_cache.set(cache_key, title)
                    return title
        except Exception as e:
            prices_logger.error(f"TEFAS fon adı çekme hatası ({fund_code}): {e}")
        return None

    def fetch_quote(self, fund_code: str, force_refresh: bool = False) -> Dict[str, Optional[float]]:
        """Fonun güncel fiyatını ve bir önceki işlem günü fiyatını döndürür.

        Returns:
            {"price": float | None, "prev_close": float | None}
        """
        cache_key = f"TEFAS_QUOTE_{fund_code}"
        if not force_refresh:
            cached = price_cache.get(cache_key)
            if cached is not None:
                return cached

        # En son tarihli iş gününü bulabilmek için son 7 günü tarıyoruz (Hafta sonu/Tatil sebebiyle)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)

        attempt = 0
        while attempt < self.max_retries:
            try:
                # 500ms bekleme, rate limit önlemi
                time.sleep(0.5)

                start_str = start_date.strftime("%Y-%m-%d")
                end_str = end_date.strftime("%Y-%m-%d")

                prices_logger.debug(f"Fetching TEFAS fund {fund_code} from {start_str} to {end_str}")
                df = self.crawler.fetch(start=start_str, end=end_str, name=fund_code, columns=["date", "code", "price"])

                if df is not None and not df.empty:
                    # En güncel tarihi al (df genelde tarihe göre sıralı gelir, yine de sort edelim)
                    df = df.sort_values(by="date", ascending=False)
                    prices = [float(p) for p in df["price"].tolist()]
                    price = prices[0]
                    prev_close = prices[1] if len(prices) >= 2 else price
                    quote = {"price": price, "prev_close": prev_close}
                    price_cache.set(cache_key, quote)
                    return quote
                else:
                    prices_logger.warning(f"No TEFAS data returned for {fund_code}")
                    return {"price": None, "prev_close": None}

            except Exception as e:
                attempt += 1
                backoff_time = (2 ** attempt)  # 2, 4, 8 saniye...
                prices_logger.error(f"Error fetching TEFAS {fund_code} (Attempt {attempt}): {e}. Retrying in {backoff_time}s")
                if attempt >= self.max_retries:
                    prices_logger.error(f"Failed to fetch TEFAS {fund_code} after {self.max_retries} attempts.")
                    return {"price": None, "prev_close": None}
                time.sleep(backoff_time)
        return {"price": None, "prev_close": None}

    def fetch_current_price(self, fund_code: str, force_refresh: bool = False) -> Optional[float]:
        """Fonun bugünkü veya işlem gören son fiyatını çeker."""
        return self.fetch_quote(fund_code, force_refresh).get("price")

    def fetch_historical_prices(self, fund_code: str, start_date: datetime, end_date: datetime) -> List[Dict[str, Any]]:
        """Verilen tarih aralığında geçmiş fiyatları döndürür."""
        try:
            start_str = start_date.strftime("%Y-%m-%d")
            end_str = end_date.strftime("%Y-%m-%d")
            
            df = self.crawler.fetch(start=start_str, end=end_str, name=fund_code, columns=["date", "code", "price"])
            
            if df is not None and not df.empty:
                # pandas datetime objesini string/date formatına çevir
                df['date'] = df['date'].dt.date
                records = df.to_dict(orient='records')
                return records
            return []
        except Exception as e:
            prices_logger.error(f"Historical fetching error for TEFAS {fund_code}: {e}")
            return []
