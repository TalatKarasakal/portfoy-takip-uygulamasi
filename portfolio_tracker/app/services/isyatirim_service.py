"""İş Yatırım (isyatirim.com.tr) yedek BIST veri kaynağı.

yfinance `.IS` kodlarında sıkça başarısız olduğu için, BIST fiyatları için
yedek kaynak. İş Yatırım'ın açık "HisseTekil" JSON endpoint'ini kullanır:

    .../Common/Data.aspx/HisseTekil?hisse=THYAO&startdate=dd-mm-yyyy&enddate=dd-mm-yyyy

Dönen kayıtlarda `HGDG_TARIH` (dd-mm-yyyy) ve `HGDG_KAPANIS` (kapanış) alanları
kullanılır. Tüm hatalar yutulur; başarısızlıkta boş/None döner.
"""

import datetime
from typing import Any, Dict, List, Optional

import httpx

from app.utils.logger import prices_logger

BASE_URL = (
    "https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/"
    "Data.aspx/HisseTekil"
)
_HEADERS = {"User-Agent": "Mozilla/5.0 (PortfolioTracker)"}


class IsYatirimService:
    @staticmethod
    def fetch_historical_prices(
        code: str, start: datetime.date, end: datetime.date
    ) -> List[Dict[str, Any]]:
        """Verilen aralık için günlük kapanışları döndürür.

        Returns:
            [{"date": date, "close_price": float}, ...] (tarihe göre artan)
        """
        code = code.upper().replace(".IS", "")
        params = {
            "hisse": code,
            "startdate": start.strftime("%d-%m-%Y"),
            "enddate": end.strftime("%d-%m-%Y"),
        }
        try:
            with httpx.Client(timeout=15.0, headers=_HEADERS) as client:
                resp = client.get(BASE_URL, params=params)
                resp.raise_for_status()
                data = resp.json()
            rows = data.get("value") or []
            records = []
            for r in rows:
                close = r.get("HGDG_KAPANIS")
                tarih = r.get("HGDG_TARIH")
                if close is None or not tarih:
                    continue
                try:
                    d = datetime.datetime.strptime(tarih, "%d-%m-%Y").date()
                except ValueError:
                    continue
                records.append({"date": d, "close_price": float(close)})
            records.sort(key=lambda x: x["date"])
            return records
        except Exception as e:
            prices_logger.error(f"İş Yatırım {code} geçmiş veri hatası: {e}")
            return []

    @staticmethod
    def fetch_quote(code: str) -> Dict[str, Optional[float]]:
        """Son kapanış ve bir önceki kapanışı döndürür."""
        end = datetime.date.today()
        start = end - datetime.timedelta(days=15)
        records = IsYatirimService.fetch_historical_prices(code, start, end)
        if not records:
            return {"price": None, "prev_close": None}
        price = records[-1]["close_price"]
        prev_close = records[-2]["close_price"] if len(records) >= 2 else price
        return {"price": price, "prev_close": prev_close}
