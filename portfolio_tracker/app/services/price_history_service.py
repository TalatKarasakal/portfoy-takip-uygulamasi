"""Günlük kapanış fiyatlarını `price_history` tablosunda saklar.

Amaç: yfinance ve İş Yatırım'ın ikisi de başarısız olduğunda (veya çevrimdışı)
son bilinen fiyatı kullanabilmek; ayrıca varlık fiyat grafiklerini ağ olmadan
besleyebilmek.
"""

import datetime
from typing import Optional

from sqlalchemy.orm import Session

from app.models.price_history import PriceHistory
from app.utils.logger import app_logger


class PriceHistoryService:
    @staticmethod
    def record_close(
        session: Session,
        asset_id: int,
        close_price: float,
        date: Optional[datetime.date] = None,
    ) -> None:
        """Belirtilen gün için kapanışı ekler/günceller (upsert)."""
        if date is None:
            date = datetime.date.today()
        if not close_price or close_price <= 0:
            return
        try:
            row = (
                session.query(PriceHistory)
                .filter(PriceHistory.asset_id == asset_id, PriceHistory.date == date)
                .first()
            )
            if row:
                row.close_price = close_price
            else:
                session.add(PriceHistory(asset_id=asset_id, date=date, close_price=close_price))
            session.commit()
        except Exception as e:  # pragma: no cover
            session.rollback()
            app_logger.error(f"price_history kaydı başarısız (asset {asset_id}): {e}")

    @staticmethod
    def last_close(session: Session, asset_id: int) -> Optional[float]:
        """Varlığın en son kayıtlı kapanışını döndürür (yoksa None)."""
        try:
            row = (
                session.query(PriceHistory)
                .filter(PriceHistory.asset_id == asset_id)
                .order_by(PriceHistory.date.desc())
                .first()
            )
            return float(row.close_price) if row else None
        except Exception as e:  # pragma: no cover
            app_logger.error(f"price_history okuma hatası (asset {asset_id}): {e}")
            return None
