import sys
import os
import time
import pandas as pd
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Add to sys.path
sys.path.insert(0, os.path.abspath('portfolio_tracker'))

from app.models.asset import Asset, AssetType
from app.models.transaction import Transaction, TransactionType
from app.models.price_history import PriceHistory
from app.models.alert import Alert
from app.database.base import Base
from app.services.import_export_service import ImportExportService

engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# Setup test data
# Generate 500 rows with 50 distinct assets
data = []
for i in range(500):
    code = f"CODE{i%50:02d}"
    data.append({
        "Kod": code,
        "Adet": 10,
        "Ortalama Maliyet": 5.5
    })
df = pd.DataFrame(data)

# Pre-insert some assets
for i in range(25):
    a = Asset(code=f"CODE{i%50:02d}", name=f"CODE{i%50:02d}", asset_type=AssetType.BIST)
    session.add(a)
session.commit()

# Measure
start_time = time.time()
ImportExportService._process_quantity_cost(session, df)
end_time = time.time()

print(f"Elapsed time: {end_time - start_time:.4f} seconds")
