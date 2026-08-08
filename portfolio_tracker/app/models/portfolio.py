"""Portföy ve portföye bağlı nakit/izleme modelleri."""

from __future__ import annotations

import enum

from sqlalchemy import Boolean, Column, Date, Enum, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.database.types import UTCDateTime, utc_now


class CashEntryType(enum.Enum):
    DEPOSIT = "DEPOSIT"
    WITHDRAWAL = "WITHDRAWAL"
    ADJUSTMENT = "ADJUSTMENT"


class Portfolio(Base):
    __tablename__ = "portfolios"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, unique=True)
    is_default = Column(Boolean, nullable=False, default=False)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)

    transactions = relationship("Transaction", back_populates="portfolio")
    snapshots = relationship("PortfolioSnapshot", back_populates="portfolio", cascade="all, delete-orphan")
    cash_entries = relationship("CashEntry", back_populates="portfolio", cascade="all, delete-orphan")
    watchlist_items = relationship("WatchlistItem", back_populates="portfolio", cascade="all, delete-orphan")


class CashEntry(Base):
    __tablename__ = "cash_entries"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    entry_type = Column(Enum(CashEntryType), nullable=False)
    date = Column(Date, nullable=False)
    amount = Column(Numeric(18, 6), nullable=False)
    note = Column(String(500), nullable=True)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)

    portfolio = relationship("Portfolio", back_populates="cash_entries")


class WatchlistItem(Base):
    __tablename__ = "watchlist_items"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "asset_id", name="uq_watchlist_portfolio_asset"),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False, index=True)
    target_price = Column(Numeric(18, 6), nullable=True)
    note = Column(String(500), nullable=True)
    created_at = Column(UTCDateTime, nullable=False, default=utc_now)

    portfolio = relationship("Portfolio", back_populates="watchlist_items")
    asset = relationship("Asset")
