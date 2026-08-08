"""Veritabanı bakım ekranının doğrulama ve kontrollü bakım işlemleri."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from app.config import BACKUP_DIR, DATABASE_FILE
from app.services.backup_service import BackupService


@dataclass(frozen=True)
class MaintenanceResult:
    success: bool
    action: str
    message: str
    details: Any = None


class DatabaseMaintenanceService:
    @staticmethod
    def integrity_check() -> MaintenanceResult:
        preview = BackupService.validate_database(DATABASE_FILE)
        return MaintenanceResult(
            bool(preview),
            "integrity",
            "Bütünlük kontrolü başarılı." if preview else preview.error,
            preview,
        )

    @staticmethod
    def list_backups() -> MaintenanceResult:
        rows = []
        for path in sorted(Path(BACKUP_DIR).glob("*.db"), reverse=True):
            preview = BackupService.validate_database(path)
            rows.append(
                {
                    "path": str(path),
                    "name": path.name,
                    "size": path.stat().st_size,
                    "valid": bool(preview),
                    "revision": preview.schema_revision,
                    "message": preview.error or preview.quick_check,
                }
            )
        return MaintenanceResult(True, "backups", f"{len(rows)} yedek bulundu.", rows)

    @staticmethod
    def restore_preview(path: str) -> MaintenanceResult:
        preview = BackupService.validate_database(path)
        return MaintenanceResult(
            bool(preview),
            "restore_preview",
            "Geri yükleme adayı doğrulandı." if preview else preview.error,
            preview,
        )

    @staticmethod
    def portable_backup(destination: str) -> MaintenanceResult:
        result = BackupService.create_backup(destination, rotate=False)
        return MaintenanceResult(
            bool(result),
            "portable_backup",
            f"Taşınabilir yedek oluşturuldu: {result.path}" if result else result.error,
            result,
        )

    @staticmethod
    def optimize() -> MaintenanceResult:
        with sqlite3.connect(str(DATABASE_FILE), timeout=10.0) as connection:
            connection.execute("PRAGMA optimize")
        return MaintenanceResult(True, "optimize", "SQLite sorgu planı optimize edildi.")

    @staticmethod
    def vacuum() -> MaintenanceResult:
        with sqlite3.connect(str(DATABASE_FILE), timeout=30.0) as connection:
            connection.execute("VACUUM")
        return MaintenanceResult(True, "vacuum", "Veritabanı VACUUM ile sıkıştırıldı.")
