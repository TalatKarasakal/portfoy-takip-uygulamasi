import os
import shutil
from datetime import datetime
import pytest

from app.services.backup_service import BackupService

@pytest.fixture
def mock_env(tmp_path, monkeypatch):
    """Mocks the DATABASE_FILE and BACKUP_DIR to use temporary directories."""
    db_file = tmp_path / "portfolio.db"
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()

    # Patch the constants in backup_service module
    monkeypatch.setattr("app.services.backup_service.DATABASE_FILE", str(db_file))
    monkeypatch.setattr("app.services.backup_service.BACKUP_DIR", str(backup_dir))

    return {"db_file": db_file, "backup_dir": backup_dir}

def test_create_backup_no_db(mock_env):
    """Test creating a backup when the database file does not exist."""
    assert BackupService.create_backup() is False
    assert len(list(mock_env["backup_dir"].iterdir())) == 0

def test_create_backup_success_no_rotation(mock_env):
    """Test successfully creating a backup without triggering rotation."""
    # Create a dummy database file
    mock_env["db_file"].write_text("dummy database content")

    assert BackupService.create_backup() is True

    # Verify backup was created
    backups = list(mock_env["backup_dir"].iterdir())
    assert len(backups) == 1
    assert backups[0].name.startswith("backup_")
    assert backups[0].name.endswith(".db")
    assert backups[0].read_text() == "dummy database content"

def test_create_backup_with_rotation(mock_env):
    """Test creating a backup and triggering the rotation logic (> 10 files)."""
    mock_env["db_file"].write_text("dummy db")

    # Create 10 dummy backup files manually
    for i in range(10):
        # Using a fixed date format to control sorting
        backup_name = f"backup_20230101_0000{i:02d}.db"
        (mock_env["backup_dir"] / backup_name).write_text("old backup")

    assert len(list(mock_env["backup_dir"].iterdir())) == 10

    # Create the 11th backup
    assert BackupService.create_backup() is True

    backups = list(mock_env["backup_dir"].iterdir())
    assert len(backups) == 10

    # The oldest backup (backup_20230101_000000.db) should have been deleted
    backup_names = [b.name for b in backups]
    assert "backup_20230101_000000.db" not in backup_names

def test_create_backup_exception(mock_env, monkeypatch):
    """Test exception handling during backup creation."""
    mock_env["db_file"].write_text("dummy db")

    def mock_copy2(*args, **kwargs):
        raise OSError("Mock error")

    monkeypatch.setattr("app.services.backup_service.shutil.copy2", mock_copy2)

    assert BackupService.create_backup() is False

def test_restore_backup_no_backup_file(mock_env):
    """Test restoring from a non-existent backup file."""
    assert BackupService.restore_backup(str(mock_env["backup_dir"] / "nonexistent.db")) is False

def test_restore_backup_success_with_existing_db(mock_env):
    """Test restoring a backup when an active database exists (creates safe copy)."""
    # Create active DB
    mock_env["db_file"].write_text("active db content")

    # Create a backup file
    backup_file = mock_env["backup_dir"] / "backup_to_restore.db"
    backup_file.write_text("restored db content")

    assert BackupService.restore_backup(str(backup_file)) is True

    # Check that the database was restored
    assert mock_env["db_file"].read_text() == "restored db content"

    # Check that the temp safety copy was created
    safety_copy = mock_env["backup_dir"] / "temp_safety_before_restore.db"
    assert safety_copy.exists()
    assert safety_copy.read_text() == "active db content"

def test_restore_backup_success_no_existing_db(mock_env):
    """Test restoring a backup when no active database exists."""
    # Ensure active DB doesn't exist
    assert not mock_env["db_file"].exists()

    # Create a backup file
    backup_file = mock_env["backup_dir"] / "backup_to_restore.db"
    backup_file.write_text("restored db content")

    assert BackupService.restore_backup(str(backup_file)) is True

    # Check that the database was restored
    assert mock_env["db_file"].exists()
    assert mock_env["db_file"].read_text() == "restored db content"

    # Temp safety copy should not exist because there was no active DB
    safety_copy = mock_env["backup_dir"] / "temp_safety_before_restore.db"
    assert not safety_copy.exists()

def test_restore_backup_exception(mock_env, monkeypatch):
    """Test exception handling during backup restoration."""
    backup_file = mock_env["backup_dir"] / "backup_to_restore.db"
    backup_file.write_text("restored db")

    def mock_copy2(*args, **kwargs):
        raise OSError("Mock error")

    monkeypatch.setattr("app.services.backup_service.shutil.copy2", mock_copy2)

    assert BackupService.restore_backup(str(backup_file)) is False
