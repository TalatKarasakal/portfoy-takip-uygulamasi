import enum
from datetime import datetime
from sqlalchemy import Column, Integer, String, Enum, DateTime
from sqlalchemy.orm import relationship
from app.database.base import Base

class AssetType(enum.Enum):
    BIST = "BIST"
    TEFAS = "TEFAS"

class Asset(Base):
    __tablename__ = "assets"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    asset_type = Column(Enum(AssetType), nullable=False)
    currency = Column(String(10), default="TRY", nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    transactions = relationship("Transaction", back_populates="asset", cascade="all, delete-orphan")
    price_histories = relationship("PriceHistory", back_populates="asset", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="asset", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Asset(code='{self.code}', type='{self.asset_type.name}')>"
