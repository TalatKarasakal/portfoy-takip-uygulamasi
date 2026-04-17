from sqlalchemy import create_engine
from app.config import DATABASE_URL
from app.database.base import Base

engine = create_engine(
    DATABASE_URL, 
    echo=False, 
    connect_args={"check_same_thread": False}
)

def init_db():
    from app.models.asset import Asset
    from app.models.transaction import Transaction
    from app.models.price_history import PriceHistory
    from app.models.portfolio_snapshot import PortfolioSnapshot
    from app.models.alert import Alert
    from app.models.settings import Settings
    
    Base.metadata.create_all(bind=engine)
