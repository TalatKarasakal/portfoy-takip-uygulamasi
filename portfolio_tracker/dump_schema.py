from sqlalchemy.schema import CreateTable
from sqlalchemy.dialects import sqlite
from app.database.engine import engine, Base
from app.models.asset import Asset
from app.models.transaction import Transaction
from app.models.price_history import PriceHistory
from app.models.portfolio_snapshot import PortfolioSnapshot
from app.models.alert import Alert
from app.models.settings import Settings

with open("app/database/migrations/initial.sql", "w") as f:
    for table in Base.metadata.sorted_tables:
        f.write(str(CreateTable(table).compile(engine, dialect=sqlite.dialect())).strip() + ";\n\n")
