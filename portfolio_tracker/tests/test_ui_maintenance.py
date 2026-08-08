import os
import sqlite3

import pytest
from PySide6.QtWidgets import QApplication, QLineEdit, QPushButton, QVBoxLayout, QWidget
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

import app.models  # noqa: F401
from app.database.base import Base
from app.services.database_maintenance_service import DatabaseMaintenanceService
from app.services.report_service import ReportMode, export_portfolio_pdf
from app.utils.app_settings import AppSettings
from app.views.accessibility import apply_accessibility


@pytest.fixture(scope="module")
def qt_app():
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    return QApplication.instance() or QApplication([])


def _valid_database(path):
    with sqlite3.connect(path) as connection:
        connection.execute("CREATE TABLE assets (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE transactions (id INTEGER PRIMARY KEY)")
        connection.execute("CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT)")
        connection.execute("CREATE TABLE alembic_version (version_num TEXT)")
        connection.execute("INSERT INTO alembic_version VALUES ('0005_dividend_plans')")


def test_database_maintenance_checks_lists_optimizes_and_vacuums(tmp_path, monkeypatch):
    from app.services import backup_service, database_maintenance_service

    database = tmp_path / "active.db"
    backups = tmp_path / "backups"
    backups.mkdir()
    _valid_database(database)
    backup = backups / "backup_test.db"
    _valid_database(backup)
    monkeypatch.setattr(database_maintenance_service, "DATABASE_FILE", database)
    monkeypatch.setattr(database_maintenance_service, "BACKUP_DIR", backups)
    monkeypatch.setattr(backup_service, "DATABASE_FILE", database)
    monkeypatch.setattr(backup_service, "BACKUP_DIR", backups)

    assert DatabaseMaintenanceService.integrity_check().success
    listed = DatabaseMaintenanceService.list_backups()
    assert listed.success and listed.details[0]["valid"]
    assert DatabaseMaintenanceService.optimize().success
    assert DatabaseMaintenanceService.vacuum().success
    portable = DatabaseMaintenanceService.portable_backup(str(tmp_path / "portable.db"))
    assert portable.success


def test_pdf_summary_and_audit_modes_create_files(tmp_path, qt_app):
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine)()
    kpi = {
        "total_value_try": 1100,
        "cash_balance_try": 100,
        "realized_pnl": 25,
        "unrealized_pnl": 75,
        "portfolio_items": [],
        "history": [{"total_value_try": 1000}, {"total_value_try": 1100}],
        "lot_analysis": [],
    }
    for mode in (ReportMode.SUMMARY, ReportMode.AUDIT):
        path = tmp_path / f"{mode.value}.pdf"
        result = export_portfolio_pdf(session, str(path), mode, None, kpi)
        assert result.success
        assert path.stat().st_size > 1000
    session.close()
    engine.dispose()


def test_accessibility_assigns_names_and_typed_settings_validate(qt_app):
    root = QWidget()
    layout = QVBoxLayout(root)
    button = QPushButton("Kaydet")
    edit = QLineEdit()
    edit.setPlaceholderText("Portföy adı")
    layout.addWidget(button)
    layout.addWidget(edit)

    apply_accessibility(root)

    assert button.accessibleName() == "Kaydet"
    assert edit.accessibleName() == "Portföy adı"
    settings = AppSettings.from_mapping(
        {"theme": "invalid", "default_currency": "EUR", "cost_method": "BAD"}
    )
    assert settings.theme == "system"
    assert settings.default_currency == "TRY"
    assert settings.cost_method == "WAC"
