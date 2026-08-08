"""Tutarlı SQLite yedekleme, doğrulama ve atomik geri yükleme işlemleri."""

from __future__ import annotations

import os
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

from app.config import BACKUP_DIR, DATABASE_FILE
from app.utils.logger import app_logger


REQUIRED_TABLES = frozenset({"assets", "transactions", "settings"})


@dataclass(frozen=True)
class RestorePreview:
    """Bir SQLite dosyasının geri yüklenebilirlik özeti."""

    success: bool
    path: Path
    quick_check: str = ""
    schema_revision: Optional[str] = None
    tables: tuple[str, ...] = ()
    error: str = ""

    def __bool__(self) -> bool:
        return self.success


@dataclass(frozen=True)
class BackupResult:
    """Yedekleme veya geri yükleme işleminin tipli sonucu."""

    success: bool
    path: Optional[Path] = None
    quick_check: str = ""
    error: str = ""

    def __bool__(self) -> bool:
        return self.success


class BackupService:
    """Canlı SQLite dosyasını ham kopyalamadan yöneten servis."""

    MAX_BACKUPS = 10

    @staticmethod
    def _database_path() -> Path:
        return Path(DATABASE_FILE)

    @staticmethod
    def _backup_dir() -> Path:
        return Path(BACKUP_DIR)

    @staticmethod
    def validate_database(path: str | Path) -> RestorePreview:
        """Dosyayı salt okunur açıp bütünlük ve asgari şema kontrolü yapar."""
        db_path = Path(path)
        if not db_path.is_file():
            return RestorePreview(False, db_path, error="Veritabanı dosyası bulunamadı.")

        try:
            uri = f"file:{db_path.resolve()}?mode=ro"
            with sqlite3.connect(uri, uri=True, timeout=5.0) as connection:
                row = connection.execute("PRAGMA quick_check").fetchone()
                quick_check = str(row[0]) if row else ""
                if quick_check.lower() != "ok":
                    return RestorePreview(
                        False,
                        db_path,
                        quick_check=quick_check,
                        error=f"SQLite bütünlük kontrolü başarısız: {quick_check}",
                    )

                tables = tuple(
                    sorted(
                        str(item[0])
                        for item in connection.execute(
                            "SELECT name FROM sqlite_master WHERE type='table'"
                        ).fetchall()
                    )
                )
                missing = REQUIRED_TABLES.difference(tables)
                if missing:
                    return RestorePreview(
                        False,
                        db_path,
                        quick_check=quick_check,
                        tables=tables,
                        error="Beklenen tablolar eksik: " + ", ".join(sorted(missing)),
                    )

                revision = None
                if "alembic_version" in tables:
                    revision_row = connection.execute(
                        "SELECT version_num FROM alembic_version LIMIT 1"
                    ).fetchone()
                    revision = str(revision_row[0]) if revision_row else None

            return RestorePreview(
                True,
                db_path,
                quick_check=quick_check,
                schema_revision=revision,
                tables=tables,
            )
        except (OSError, sqlite3.Error) as exc:
            return RestorePreview(False, db_path, error=f"Veritabanı doğrulanamadı: {exc}")

    @staticmethod
    def _copy_with_sqlite_backup(source: Path, destination: Path) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            destination.unlink()
        with sqlite3.connect(str(source), timeout=10.0) as source_connection:
            with sqlite3.connect(str(destination), timeout=10.0) as target_connection:
                source_connection.backup(target_connection)

    @staticmethod
    def _rotate_backups() -> None:
        backup_dir = BackupService._backup_dir()
        candidates = sorted(
            (
                path
                for path in backup_dir.glob("backup_*.db")
                if "preimplementation" not in path.name
            ),
            key=lambda path: path.stat().st_mtime,
        )
        for old_path in candidates[:-BackupService.MAX_BACKUPS]:
            old_path.unlink()
            app_logger.info("Eski doğrulanmış yedek silindi: %s", old_path)

    @staticmethod
    def maybe_auto_backup(days: int = 7) -> bool:
        """Son başarılı yedekten yeterince zaman geçtiyse doğrulanmış yedek alır."""
        try:
            from app.database.session import get_session
            from app.models.settings import Settings

            with get_session() as session:
                row = session.query(Settings).filter_by(key="last_backup_date").first()
                last_str = row.value if row else None
                needs_backup = True
                if last_str:
                    try:
                        last = datetime.strptime(last_str, "%Y-%m-%d")
                        needs_backup = datetime.now() - last >= timedelta(days=days)
                    except ValueError:
                        needs_backup = True

                if not needs_backup:
                    return False

                result = BackupService.create_backup()
                if not result:
                    return False

                today = datetime.now().strftime("%Y-%m-%d")
                if row:
                    row.value = today
                else:
                    session.add(Settings(key="last_backup_date", value=today))
                session.commit()
                return True
        except Exception as exc:  # pragma: no cover - açılış güvenlik ağı
            app_logger.error("Otomatik yedek başarısız: %s", exc)
            return False

    @staticmethod
    def create_backup(
        destination: str | Path | None = None,
        *,
        rotate: bool = True,
    ) -> BackupResult:
        """SQLite Backup API ile geçici dosyaya yazıp doğrulanmış yedek üretir."""
        database_path = BackupService._database_path()
        if not database_path.is_file():
            message = "Veritabanı dosyası bulunamadığı için yedek alınamadı."
            app_logger.warning(message)
            return BackupResult(False, error=message)

        backup_dir = BackupService._backup_dir()
        backup_dir.mkdir(parents=True, exist_ok=True)
        if destination is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            final_path = backup_dir / f"backup_{timestamp}.db"
        else:
            final_path = Path(destination)
        temporary_path = final_path.with_suffix(final_path.suffix + ".tmp")

        try:
            BackupService._copy_with_sqlite_backup(database_path, temporary_path)
            preview = BackupService.validate_database(temporary_path)
            if not preview:
                raise sqlite3.DatabaseError(preview.error)
            os.replace(temporary_path, final_path)
            if rotate:
                BackupService._rotate_backups()
            app_logger.info("Veritabanı yedeği doğrulandı: %s", final_path)
            return BackupResult(True, final_path, quick_check=preview.quick_check)
        except (OSError, sqlite3.Error) as exc:
            if temporary_path.exists():
                temporary_path.unlink()
            message = f"Yedekleme başarısız: {exc}"
            app_logger.error(message)
            return BackupResult(False, error=message)

    @staticmethod
    def restore_backup(backup_file_path: str | Path) -> BackupResult:
        """Doğrulanmış aday dosyayı güvenlik yedeği sonrasında atomik geri yükler."""
        candidate = Path(backup_file_path)
        preview = BackupService.validate_database(candidate)
        if not preview:
            app_logger.error("Geri yükleme adayı reddedildi: %s", preview.error)
            return BackupResult(False, error=preview.error)

        database_path = BackupService._database_path()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        safety_path = BackupService._backup_dir() / f"safety_before_restore_{timestamp}.db"
        staging_path = database_path.with_suffix(database_path.suffix + ".restore.tmp")

        safety_result: Optional[BackupResult] = None
        if database_path.exists():
            safety_result = BackupService.create_backup(safety_path, rotate=False)
            if not safety_result:
                return BackupResult(
                    False,
                    error="Aktif veritabanının güvenlik yedeği alınamadığı için geri yükleme durduruldu.",
                )

        try:
            from app.database.engine import engine

            engine.dispose()
            BackupService._copy_with_sqlite_backup(candidate, staging_path)
            staged_preview = BackupService.validate_database(staging_path)
            if not staged_preview:
                raise sqlite3.DatabaseError(staged_preview.error)

            os.replace(staging_path, database_path)
            for suffix in ("-wal", "-shm"):
                sidecar = Path(str(database_path) + suffix)
                if sidecar.exists():
                    sidecar.unlink()
            app_logger.info("Veritabanı atomik olarak geri yüklendi: %s", candidate)
            return BackupResult(True, database_path, quick_check=staged_preview.quick_check)
        except (OSError, sqlite3.Error) as exc:
            if staging_path.exists():
                staging_path.unlink()
            if safety_result and safety_result.path:
                try:
                    BackupService._copy_with_sqlite_backup(safety_result.path, staging_path)
                    os.replace(staging_path, database_path)
                except (OSError, sqlite3.Error) as rollback_exc:  # pragma: no cover
                    app_logger.critical("Geri yükleme rollback başarısız: %s", rollback_exc)
            message = f"Geri yükleme başarısız: {exc}"
            app_logger.error(message)
            return BackupResult(False, error=message)
