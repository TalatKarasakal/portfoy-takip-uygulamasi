import enum

from sqlalchemy import Column, Date, Enum, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.database.types import UTCDateTime, utc_now


class TransactionType(enum.Enum):
    BUY = "BUY"
    SELL = "SELL"
    DIVIDEND = "DIVIDEND"  # Temettü: nakit girişi, adet değişmez
    SPLIT = "SPLIT"        # Bedelsiz/bölünme: adet katsayıyla çarpılır, maliyet bölünür

class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    portfolio_id = Column(Integer, ForeignKey("portfolios.id"), nullable=False, default=1)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    transaction_type = Column(Enum(TransactionType), nullable=False)
    date = Column(Date, nullable=False)
    quantity = Column(Numeric(precision=18, scale=6), nullable=False)
    unit_price = Column(Numeric(precision=18, scale=6), nullable=False)
    commission = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    tax = Column(Numeric(precision=18, scale=6), default=0, nullable=False)
    note = Column(String(500), nullable=True)
    created_at = Column(UTCDateTime, default=utc_now)

    asset = relationship("Asset", back_populates="transactions")
    portfolio = relationship("Portfolio", back_populates="transactions")

    @property
    def total_cost(self):
        base_amount = float(self.quantity) * float(self.unit_price)
        return base_amount + float(self.commission) + float(self.tax)
