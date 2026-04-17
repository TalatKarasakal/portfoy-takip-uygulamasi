from datetime import datetime
from sqlalchemy import Column, Integer, ForeignKey, Date, Numeric, UniqueConstraint
from sqlalchemy.orm import relationship
from app.database.base import Base

class PriceHistory(Base):
    __tablename__ = "price_history"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    date = Column(Date, nullable=False)
    close_price = Column(Numeric(precision=18, scale=6), nullable=False)

    __table_args__ = (UniqueConstraint('asset_id', 'date', name='uq_asset_date'),)

    asset = relationship("Asset", back_populates="price_histories")
