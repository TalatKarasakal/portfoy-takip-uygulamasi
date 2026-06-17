from sqlalchemy import create_engine

from app.config import DATABASE_URL
from app.database.base import Base

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False}
)

def init_db():

    Base.metadata.create_all(bind=engine)
