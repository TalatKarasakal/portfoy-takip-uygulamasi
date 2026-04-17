from sqlalchemy import Column, String
from app.database.base import Base

class Settings(Base):
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True, index=True)
    value = Column(String(255), nullable=True)
