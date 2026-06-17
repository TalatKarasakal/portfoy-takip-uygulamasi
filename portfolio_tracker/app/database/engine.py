from sqlalchemy import create_engine

from app.config import DATABASE_URL
from app.database.base import Base

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

def init_db():
    # SQLAlchemy mapper'ının tüm tabloları tanıması için modeller, create_all'dan
    # ÖNCE import edilmeli (yan-etki importu). Aksi halde "failed to locate a name"
    # hatası alınır. noqa: ruff bunları "kullanılmıyor" sanmasın.
    from app.models import (  # noqa: F401
        Alert,
        Asset,
        PortfolioSnapshot,
        PriceHistory,
        Settings,
        Transaction,
    )

    Base.metadata.create_all(bind=engine)
