from sqlalchemy.dialects import sqlite
from sqlalchemy.schema import CreateTable

from app.database.engine import Base, engine

with open("app/database/migrations/initial.sql", "w") as f:
    for table in Base.metadata.sorted_tables:
        f.write(str(CreateTable(table).compile(engine, dialect=sqlite.dialect())).strip() + ";\n\n")
