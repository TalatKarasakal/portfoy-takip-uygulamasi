import sqlite3
from decimal import Decimal

import pytest
from alembic import command
from sqlalchemy import create_engine

import app.models  # noqa: F401
from app.database.migration_service import (
    MigrationError,
    MigrationService,
    alembic_config,
)
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
    assert revision == "0004_remove_secrets"
    assert {"assets", "transactions", "settings", "portfolios", "cash_entries"}.issubset(tables)
    engine.dispose()


def test_legacy_database_requires_approval_and_is_stamped(tmp_path):
    database = tmp_path / "legacy.db"
    engine = _engine(database)
    command.upgrade(alembic_config(str(engine.url)), "0001_initial")
    with engine.begin() as connection:
        connection.exec_driver_sql("DROP TABLE alembic_version")
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
    assert revision == "0004_remove_secrets"
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


def test_legacy_migration_infers_opening_cash_and_adds_query_index(tmp_path):
    database = tmp_path / "legacy_with_data.db"
    engine = _engine(database)
    command.upgrade(alembic_config(str(engine.url)), "0001_initial")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO assets (id, code, name, asset_type, currency) "
            "VALUES (1, 'THYAO', 'THYAO', 'BIST', 'TRY')"
        )
        connection.exec_driver_sql(
            """
            INSERT INTO transactions
                (id, asset_id, transaction_type, date, quantity, unit_price,
                 commission, tax)
            VALUES (1, 1, 'BUY', '2024-01-02', 10, 100, 2, 0)
            """
        )
        connection.exec_driver_sql("DROP TABLE alembic_version")

    MigrationService.ensure_current(
        engine, approved=True, backup_callback=lambda: BackupResult(True)
    )

    with sqlite3.connect(database) as connection:
        opening = connection.execute(
            "SELECT amount FROM cash_entries WHERE note='Migration açılış bakiyesi'"
        ).fetchone()[0]
        plan = connection.execute(
            "EXPLAIN QUERY PLAN SELECT * FROM transactions "
            "WHERE portfolio_id=1 AND asset_id=1 ORDER BY date, id"
        ).fetchall()
    assert Decimal(str(opening)) == Decimal("1002")
    assert any("ix_transactions_portfolio_asset_date_id" in str(row) for row in plan)
    engine.dispose()


def test_plaintext_gemini_key_is_removed_by_migration(tmp_path):
    database = tmp_path / "secret.db"
    engine = _engine(database)
    config = alembic_config(str(engine.url))
    command.upgrade(config, "0003_import_batches")
    with engine.begin() as connection:
        connection.exec_driver_sql(
            "INSERT INTO settings (key, value) VALUES "
            "('ai_gemini_api_key', 'must-not-remain')"
        )

    command.upgrade(config, "head")

    with sqlite3.connect(database) as connection:
        row = connection.execute(
            "SELECT value FROM settings WHERE key='ai_gemini_api_key'"
        ).fetchone()
    assert row is None
    engine.dispose()
