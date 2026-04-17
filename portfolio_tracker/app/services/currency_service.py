import httpx
import xml.etree.ElementTree as ET
from typing import Optional
from app.utils.logger import prices_logger
from app.utils.cache import price_cache

class CurrencyService:
    TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"

    def fetch_usd_try(self, force_refresh: bool = False) -> Optional[float]:
        """TCMB'den güncel USD/TRY Efektif Satış (veya Döviz Satış) kurunu çeker."""
        cache_key = "CURRENCY_USD_TRY"
        
        if not force_refresh:
            cached_price = price_cache.get(cache_key)
            if cached_price is not None:
                return float(cached_price)

        try:
            prices_logger.debug("Fetching USD/TRY exchange rate from TCMB")
            with httpx.Client(timeout=10.0) as client:
                response = client.get(self.TCMB_URL)
                response.raise_for_status()
                
            xml_data = response.text
            root = ET.fromstring(xml_data)
            
            # USD düğümünü bul
            usd_node = root.find(".//Currency[@Kod='USD']")
            if usd_node is not None:
                # ForexSelling (Döviz Satış) genelde referans alınır.
                selling_node = usd_node.find("ForexSelling")
                if selling_node is not None and selling_node.text:
                    rate = float(selling_node.text.strip())
                    # Döviz kuru 24 saat geçerli sayılabiliyor ama cache'imiz standart 15 dk işler
                    # Farklı bir TTL uygulamak istenirse cache.set'e özel parametre verilebilir.
                    price_cache.set(cache_key, rate)
                    return rate
            
            prices_logger.warning("USD rate not found in TCMB XML structure")
            return None
            
        except Exception as e:
            prices_logger.error(f"Error fetching USD/TRY from TCMB: {e}")
            return None
