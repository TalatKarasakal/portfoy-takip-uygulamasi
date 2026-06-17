import time
from typing import Any, Dict, Optional, Tuple


class PriceCache:
    """Basit in-memory fiyat önbelleği. 15 dk (900 sn) TTL kullanır."""
    _cache: Dict[str, Tuple[float, Any]] = {}  # { asset_code: (timestamp, price) }
    DEFAULT_TTL: int = 900  # 15 dakika

    @classmethod
    def get(cls, asset_code: str) -> Optional[Any]:
        if asset_code in cls._cache:
            timestamp, price = cls._cache[asset_code]
            if time.time() - timestamp < cls.DEFAULT_TTL:
                return price
            else:
                del cls._cache[asset_code]
        return None

    @classmethod
    def set(cls, asset_code: str, price: Any) -> None:
        cls._cache[asset_code] = (time.time(), price)

    @classmethod
    def clear(cls) -> None:
        """Cache temizliği ('Şimdi Yenile' dendiğinde kullanılır)."""
        cls._cache.clear()

price_cache = PriceCache()
