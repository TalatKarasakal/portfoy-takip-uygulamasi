import sqlite3

import pytest

from app.services.backup_service import BackupService


def _create_portfolio_database(path, marker="active"):
    with sqlite3.connect(path) as connection:
        connection.executescript(
            """
            CREATE TABLE assets (id INTEGER PRIMARY KEY, code TEXT);
            CREATE TABLE transactions (id INTEGER PRIMARY KEY, asset_id INTEGER);
            CREATE TABLE settings (key TEXT PRIMARY KEY, value TEXT);
            """
        )
        connection.execute("INSERT INTO settings VALUES ('marker', ?)", (marker,))


def _marker(path):
    with sqlite3.connect(path) as connection:
        return connection.execute(
            "SELECT value FROM settings WHERE key='marker'"
        ).fetchone()[0]


@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    db_file = tmp_path / "portfolio.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    monkeypatch.setattr("app.services.backup_service.DATABASE_FILE", db_file)
    monkeypatch.setattr("app.services.backup_service.BACKUP_DIR", backup_dir)
    return {"db_file": db_file, "backup_dir": backup_dir}


def test_create_backup_no_db(mock_env):
    result = BackupService.create_backup()
    assert not result
    assert not list(mock_env["backup_dir"].iterdir())


def test_create_backup_is_valid_sqlite_snapshot(mock_env):
    _create_portfolio_database(mock_env["db_file"])

    result = BackupService.create_backup()

    assert result
    assert result.path is not None
    assert BackupService.validate_database(result.path)
    assert _marker(result.path) == "active"


def test_create_backup_succeeds_during_active_write_transaction(mock_env):
    _create_portfolio_database(mock_env["db_file"])
    writer = sqlite3.connect(mock_env["db_file"], timeout=5.0)
    try:
        writer.execute("BEGIN IMMEDIATE")
        writer.execute("UPDATE settings SET value='uncommitted' WHERE key='marker'")

        result = BackupService.create_backup()

        assert result
        assert _marker(result.path) == "active"
        assert BackupService.validate_database(result.path).quick_check == "ok"
    finally:
        writer.rollback()
        writer.close()


def test_create_backup_rotates_only_regular_backups(mock_env):
    _create_portfolio_database(mock_env["db_file"])
    protected = mock_env["backup_dir"] / "backup_20260808_preimplementation.db"
    _create_portfolio_database(protected, "protected")
    for index in range(10):
        path = mock_env["backup_dir"] / f"backup_20230101_0000{index:02d}.db"
        _create_portfolio_database(path, str(index))

    assert BackupService.create_backup()

    regular = [
        path
        for path in mock_env["backup_dir"].glob("backup_*.db")
        if "preimplementation" not in path.name
    ]
    assert len(regular) == 10
    assert protected.exists()


def test_create_backup_exception_cleans_temporary_file(mock_env, monkeypatch):
    _create_portfolio_database(mock_env["db_file"])

    def fail_copy(*_args, **_kwargs):
        raise OSError("Mock error")

    monkeypatch.setattr(BackupService, "_copy_with_sqlite_backup", fail_copy)
    result = BackupService.create_backup()

    assert not result
    assert not list(mock_env["backup_dir"].glob("*.tmp"))


def test_validate_rejects_corrupt_and_wrong_schema(mock_env):
    corrupt = mock_env["backup_dir"] / "corrupt.db"
    corrupt.write_text("not sqlite", encoding="utf-8")
    wrong = mock_env["backup_dir"] / "wrong.db"
    with sqlite3.connect(wrong) as connection:
        connection.execute("CREATE TABLE unrelated (id INTEGER PRIMARY KEY)")

    assert not BackupService.validate_database(corrupt)
    preview = BackupService.validate_database(wrong)
    assert not preview
    assert "eksik" in preview.error


def test_restore_backup_rejects_invalid_candidate_without_touching_active(mock_env):
    _create_portfolio_database(mock_env["db_file"], "active")
    candidate = mock_env["backup_dir"] / "invalid.db"
    candidate.write_text("invalid", encoding="utf-8")

    result = BackupService.restore_backup(candidate)

    assert not result
    assert _marker(mock_env["db_file"]) == "active"


def test_restore_backup_is_atomic_and_creates_safety_copy(mock_env):
    _create_portfolio_database(mock_env["db_file"], "active")
    candidate = mock_env["backup_dir"] / "candidate.db"
    _create_portfolio_database(candidate, "restored")

    result = BackupService.restore_backup(candidate)

    assert result
    assert _marker(mock_env["db_file"]) == "restored"
    safety_files = list(mock_env["backup_dir"].glob("safety_before_restore_*.db"))
    assert len(safety_files) == 1
    assert _marker(safety_files[0]) == "active"


def test_restore_stops_when_safety_backup_fails(mock_env, monkeypatch):
    _create_portfolio_database(mock_env["db_file"], "active")
    candidate = mock_env["backup_dir"] / "candidate.db"
    _create_portfolio_database(candidate, "restored")
    original = BackupService.create_backup

    def fail_safety(destination=None, *, rotate=True):
        if destination is not None:
            from app.services.backup_service import BackupResult

            return BackupResult(False, error="forced")
        return original(destination, rotate=rotate)

    monkeypatch.setattr(BackupService, "create_backup", fail_safety)

    result = BackupService.restore_backup(candidate)

    assert not result
    assert _marker(mock_env["db_file"]) == "active"
