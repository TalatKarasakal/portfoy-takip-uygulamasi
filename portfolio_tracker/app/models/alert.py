import enum

from sqlalchemy import Boolean, Column, Enum, ForeignKey, Integer, Numeric
from sqlalchemy.orm import relationship

from app.database.base import Base
from app.database.types import UTCDateTime, utc_now


class AlertType(enum.Enum):
    PRICE_ABOVE = "PRICE_ABOVE"
    PRICE_BELOW = "PRICE_BELOW"
    PCT_CHANGE_ABOVE = "PCT_CHANGE_ABOVE"
    PCT_CHANGE_BELOW = "PCT_CHANGE_BELOW"

class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)
    asset_id = Column(Integer, ForeignKey("assets.id"), nullable=False)
    alert_type = Column(Enum(AlertType), nullable=False)
    threshold = Column(Numeric(precision=18, scale=6), nullable=False)
    is_active = Column(Boolean, default=True)
    triggered_at = Column(UTCDateTime, nullable=True)
    created_at = Column(UTCDateTime, default=utc_now)

    asset = relationship("Asset", back_populates="alerts")
