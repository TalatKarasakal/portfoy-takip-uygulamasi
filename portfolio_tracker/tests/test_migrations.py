import sqlite3

import pytest
from sqlalchemy import create_engine

import app.models  # noqa: F401
from app.database.base import Base
from app.database.migration_service import MigrationError, MigrationService
from app.services.backup_service import BackupResult


def _engine(path):
    return create_engine(f"sqlite:///{path}")


def test_new_database_is_created_at_head(tmp_path):
    database = tmp_path / "new.db"
    engine = _engine(database)

    plan = MigrationService.inspect_plan(engine)
    assert plan.is_new_database
    MigrationService.ensure_current(engine)

    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
        tables = {
            row[0]
            for row in connection.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    assert revision == "0001_initial"
    assert {"assets", "transactions", "settings"}.issubset(tables)
    engine.dispose()


def test_legacy_database_requires_approval_and_is_stamped(tmp_path):
    database = tmp_path / "legacy.db"
    engine = _engine(database)
    Base.metadata.create_all(engine)
    plan = MigrationService.inspect_plan(engine)
    assert plan.is_legacy
    assert plan.requires_backup

    with pytest.raises(MigrationError, match="onayı"):
        MigrationService.ensure_current(engine)

    backups = []

    def backup():
        backups.append(True)
        return BackupResult(True)

    MigrationService.ensure_current(engine, approved=True, backup_callback=backup)
    with sqlite3.connect(database) as connection:
        revision = connection.execute("SELECT version_num FROM alembic_version").fetchone()[0]
    assert revision == "0001_initial"
    assert backups == [True]
    engine.dispose()


def test_unknown_schema_is_rejected(tmp_path):
    database = tmp_path / "unknown.db"
    with sqlite3.connect(database) as connection:
        connection.execute("CREATE TABLE something_else (id INTEGER PRIMARY KEY)")
    engine = _engine(database)

    with pytest.raises(MigrationError, match="Bilinmeyen"):
        MigrationService.inspect_plan(engine)
    engine.dispose()
