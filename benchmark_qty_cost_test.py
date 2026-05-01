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

def _process_quantity_cost_optimized(session, df: pd.DataFrame) -> bool:
    import datetime

    # 1. Pre-fetch all needed assets
    # Get unique codes from the dataframe
    codes = []
    for _, row in df.iterrows():
        code = str(row.get("Kod", row.get("kod"))).strip().upper()
        if not pd.isna(code) and code:
            codes.append(code)

    unique_codes = set(codes)

    # Fetch existing assets into a dictionary
    existing_assets = session.query(Asset).filter(Asset.code.in_(unique_codes)).all()
    asset_dict = {a.code: a for a in existing_assets}

    for index, row in df.iterrows():
        code = str(row.get("Kod", row.get("kod"))).strip().upper()
        if pd.isna(code) or not code:
            continue

        asset = asset_dict.get(code)
        if not asset:
            a_type = AssetType.BIST if len(code) == 5 else AssetType.TEFAS
            asset = Asset(code=code, name=code, asset_type=a_type)
            session.add(asset)
            session.flush()
            asset_dict[code] = asset

        tx = Transaction(
            asset_id=asset.id,
            transaction_type=TransactionType.BUY,
            date=datetime.date.today(),
            quantity=row.get("Adet", row.get("adet", 0)),
            unit_price=row.get("Ortalama Maliyet", row.get("maliyet", row.get("ortalama_maliyet", 0))),
            commission=0,
            tax=0,
            note="Excel Import - Toplu Maliyet"
        )
        session.add(tx)
    session.commit()
    return True


engine = create_engine('sqlite:///:memory:')
Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)
session = SessionLocal()

# Setup test data
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
_process_quantity_cost_optimized(session, df)
end_time = time.time()

print(f"Elapsed time: {end_time - start_time:.4f} seconds")
