from sqlalchemy import Column, Integer, Date, Numeric
from app.database.base import Base

class PortfolioSnapshot(Base):
    __tablename__ = "portfolio_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    date = Column(Date, nullable=False, unique=True)
    total_value_try = Column(Numeric(precision=18, scale=6), nullable=False)
    total_value_usd = Column(Numeric(precision=18, scale=6), nullable=False)
    total_cost_try = Column(Numeric(precision=18, scale=6), nullable=False)
    unrealized_pnl_try = Column(Numeric(precision=18, scale=6), nullable=False)
