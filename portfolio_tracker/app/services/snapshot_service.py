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
        portfolio_id: int = 1,
        cash_balance_try: float = 0.0,
        net_external_flow_try: float = 0.0,
    ) -> None:
        """Bugünün portföy snapshot'ını ekler veya günceller (upsert)."""
        if snapshot_date is None:
            snapshot_date = datetime.date.today()
        try:
            existing = (
                session.query(PortfolioSnapshot)
                .filter(
                    PortfolioSnapshot.portfolio_id == portfolio_id,
                    PortfolioSnapshot.date == snapshot_date,
                )
                .first()
            )
            if existing:
                existing.total_value_try = total_value_try
                existing.total_value_usd = total_value_usd
                existing.total_cost_try = total_cost_try
                existing.unrealized_pnl_try = unrealized_pnl_try
                existing.cash_balance_try = cash_balance_try
                existing.net_external_flow_try = net_external_flow_try
                existing.calculation_version = 2
            else:
                session.add(
                    PortfolioSnapshot(
                        date=snapshot_date,
                        portfolio_id=portfolio_id,
                        total_value_try=total_value_try,
                        total_value_usd=total_value_usd,
                        total_cost_try=total_cost_try,
                        unrealized_pnl_try=unrealized_pnl_try,
                        cash_balance_try=cash_balance_try,
                        net_external_flow_try=net_external_flow_try,
                        calculation_version=2,
                    )
                )
            session.commit()
        except Exception as e:  # pragma: no cover - savunma amaçlı
            session.rollback()
            app_logger.error(f"Snapshot kaydı başarısız: {e}")

    @staticmethod
    def get_history(
        session: Session,
        days: Optional[int] = None,
        portfolio_id: Optional[int] = 1,
        calculation_version: Optional[int] = None,
    ) -> List[Dict[str, Any]]:
        """Snapshot geçmişini tarih sırasıyla döndürür.

        Args:
            days: Yalnızca son N günü döndür (None ise tümü).
        """
        try:
            query = session.query(PortfolioSnapshot)
            if portfolio_id is not None:
                query = query.filter(PortfolioSnapshot.portfolio_id == portfolio_id)
            if calculation_version is not None:
                query = query.filter(PortfolioSnapshot.calculation_version == calculation_version)
            query = query.order_by(PortfolioSnapshot.date.asc())
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
                    "portfolio_id": r.portfolio_id,
                    "cash_balance_try": float(r.cash_balance_try),
                    "net_external_flow_try": float(r.net_external_flow_try),
                    "calculation_version": r.calculation_version,
                }
                for r in rows
            ]
        except Exception as e:  # pragma: no cover
            app_logger.error(f"Snapshot geçmişi okunamadı: {e}")
            return []

    @staticmethod
    def get_consolidated_history(
        session: Session, days: Optional[int] = None, calculation_version: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Portföy snapshot'larını tarih bazında konsolide eder."""
        rows = SnapshotService.get_history(
            session,
            days=days,
            portfolio_id=None,
            calculation_version=calculation_version,
        )
        grouped: Dict[datetime.date, Dict[str, Any]] = {}
        for row in rows:
            target = grouped.setdefault(
                row["date"],
                {
                    "date": row["date"],
                    "total_value_try": 0.0,
                    "total_value_usd": 0.0,
                    "total_cost_try": 0.0,
                    "unrealized_pnl_try": 0.0,
                    "cash_balance_try": 0.0,
                    "net_external_flow_try": 0.0,
                    "calculation_version": row["calculation_version"],
                    "portfolio_id": None,
                },
            )
            for key in (
                "total_value_try",
                "total_value_usd",
                "total_cost_try",
                "unrealized_pnl_try",
                "cash_balance_try",
                "net_external_flow_try",
            ):
                target[key] += row[key]
        return [grouped[key] for key in sorted(grouped)]
