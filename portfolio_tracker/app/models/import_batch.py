"""İçe aktarma batch kaydı ve geri alma durumu."""

from __future__ import annotations

import enum

from sqlalchemy import Column, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.database.types import UTCDateTime, utc_now


class ImportBatchStatus(enum.Enum):
    APPLIED = "APPLIED"
    UNDONE = "UNDONE"


class ImportBatch(Base):
    __tablename__ = "import_batches"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=True, index=True)
    source_name = Column(String(255), nullable=False)
    source_type = Column(String(30), nullable=False, default="EXCEL")
    status = Column(Enum(ImportBatchStatus), nullable=False, default=ImportBatchStatus.APPLIED)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)
    undone_at = Column(UTCDateTime, nullable=True)

    transactions = relationship("Transaction", back_populates="import_batch")
    cash_entries = relationship("CashEntry", back_populates="import_batch")
    watchlist_items = relationship("WatchlistItem", back_populates="import_batch")
    dividend_plans = relationship("DividendPlan", back_populates="import_batch")
