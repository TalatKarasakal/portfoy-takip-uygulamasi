from sqlalchemy.orm import sessionmaker
from app.database.engine import engine

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def get_session():
    """Context manager olmaksızın manual session almak için."""
    return SessionLocal()
