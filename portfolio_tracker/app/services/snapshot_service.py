"""Portföyün günlük toplam değerini saklayan snapshot servisi.

Zaman serisi grafiklerinin (dashboard ve analiz) gerçek geçmiş veriye
dayanması için her başarılı fiyat yenilemesinde günde bir kez snapshot
yazılır (aynı gün tekrar yazılırsa üzerine güncellenir).
"""

import datetime
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models.portfolio_snapshot import PortfolioSnapshot
from app.utils.logger import app_logger


class SnapshotService:
    @staticmethod
    def record_snapshot(
        session: Session,
        total_value_try: float,
        total_cost_try: float,
        unrealized_pnl_try: float,
        total_value_usd: float = 0.0,
        snapshot_date: Optional[datetime.date] = None,
    ) -> None:
        """Bugünün portföy snapshot'ını ekler veya günceller (upsert)."""
        if snapshot_date is None:
            snapshot_date = datetime.date.today()
        try:
            existing = (
                session.query(PortfolioSnapshot)
                .filter(PortfolioSnapshot.date == snapshot_date)
                .first()
            )
            if existing:
                existing.total_value_try = total_value_try
                existing.total_value_usd = total_value_usd
                existing.total_cost_try = total_cost_try
                existing.unrealized_pnl_try = unrealized_pnl_try
            else:
                session.add(
                    PortfolioSnapshot(
                        date=snapshot_date,
                        total_value_try=total_value_try,
                        total_value_usd=total_value_usd,
                        total_cost_try=total_cost_try,
                        unrealized_pnl_try=unrealized_pnl_try,
                    )
                )
            session.commit()
        except Exception as e:  # pragma: no cover - savunma amaçlı
            session.rollback()
            app_logger.error(f"Snapshot kaydı başarısız: {e}")

    @staticmethod
    def get_history(session: Session, days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Snapshot geçmişini tarih sırasıyla döndürür.

        Args:
            days: Yalnızca son N günü döndür (None ise tümü).
        """
        try:
            query = session.query(PortfolioSnapshot).order_by(PortfolioSnapshot.date.asc())
            rows = query.all()
            if days is not None and rows:
                cutoff = datetime.date.today() - datetime.timedelta(days=days)
                rows = [r for r in rows if r.date >= cutoff]
            return [
                {
                    "date": r.date,
                    "total_value_try": float(r.total_value_try),
                    "total_value_usd": float(r.total_value_usd),
                    "total_cost_try": float(r.total_cost_try),
                    "unrealized_pnl_try": float(r.unrealized_pnl_try),
                }
                for r in rows
            ]
        except Exception as e:  # pragma: no cover
            app_logger.error(f"Snapshot geçmişi okunamadı: {e}")
            return []
