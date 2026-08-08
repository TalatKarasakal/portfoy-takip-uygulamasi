"""Manuel temettü planı ve bağlı ödeme işlemi."""

from __future__ import annotations

import enum

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.database.types import UTCDateTime, utc_now


class DividendPlanStatus(enum.Enum):
    PLANNED = "PLANNED"
    PAID = "PAID"
    CANCELLED = "CANCELLED"


class DividendPlan(Base):
    __tablename__ = "dividend_plans"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    payment_date = Column(Date, nullable=False, index=True)
    gross_per_share = Column(Numeric(18, 6), nullable=False)
    expected_quantity = Column(Numeric(18, 6), nullable=True)
    status = Column(Enum(DividendPlanStatus), nullable=False, default=DividendPlanStatus.PLANNED)
    linked_transaction_id = Column(
        Integer,
        ForeignKey("transactions.id"),
        nullable=True,
        unique=True,
    )
    import_batch_id = Column(Integer, ForeignKey("import_batches.id"), nullable=True, index=True)
    note = Column(String(500), nullable=True)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)

    portfolio = relationship("Portfolio", back_populates="dividend_plans")
    asset = relationship("Asset", back_populates="dividend_plans")
    linked_transaction = relationship("Transaction", back_populates="dividend_plan")
    import_batch = relationship("ImportBatch", back_populates="dividend_plans")
