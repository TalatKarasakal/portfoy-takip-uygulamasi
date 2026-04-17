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

    def fetch_current_price(self, fund_code: str, force_refresh: bool = False) -> Optional[float]:
        """Fonun bugünkü veya işlem gören son fiyatını çeker."""
        if not force_refresh:
            cached_price = price_cache.get(f"TEFAS_{fund_code}")
            if cached_price is not None:
                return float(cached_price)

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
                    latest_price = float(df.iloc[0]["price"])
                    
                    # Cache'e kaydet
                    price_cache.set(f"TEFAS_{fund_code}", latest_price)
                    return latest_price
                else:
                    prices_logger.warning(f"No TEFAS data returned for {fund_code}")
                    return None
                    
            except Exception as e:
                attempt += 1
                backoff_time = (2 ** attempt)  # 2, 4, 8 saniye...
                prices_logger.error(f"Error fetching TEFAS {fund_code} (Attempt {attempt}): {e}. Retrying in {backoff_time}s")
                if attempt >= self.max_retries:
                    prices_logger.error(f"Failed to fetch TEFAS {fund_code} after {self.max_retries} attempts.")
                    return None
                time.sleep(backoff_time)
        return None

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
