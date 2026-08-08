from sqlalchemy import Column, Date, ForeignKey, Integer, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship

from app.database.base import Base


class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"
    __table_args__ = (
        UniqueConstraint("portfolio_id", "date", name="uq_snapshot_portfolio_date"),
    )

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, default=1)
    date = Column(Date, nullable=False)
    total_value_try = Column(Numeric(precision=18, scale=6), nullable=False)
    total_value_usd = Column(Numeric(precision=18, scale=6), nullable=False)
    total_cost_try = Column(Numeric(precision=18, scale=6), nullable=False)
    unrealized_pnl_try = Column(Numeric(precision=18, scale=6), nullable=False)
    cash_balance_try = Column(Numeric(precision=18, scale=6), nullable=False, default=0)
    net_external_flow_try = Column(Numeric(precision=18, scale=6), nullable=False, default=0)
    calculation_version = Column(Integer, nullable=False, default=2)

    portfolio = relationship("Portfolio", back_populates="snapshots")
