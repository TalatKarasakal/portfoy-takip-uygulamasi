from sqlalchemy import Column, String, Text

from app.database.base import Base


class Settings(Base):
    __tablename__ = "settings"

    key = Column(String(50), primary_key=True, index=True)
    value = Column(Text, nullable=True)
