"""Uygulama açılışında güvenli Alembic migration yönetimi."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import Engine, inspect

from app.config import DATABASE_FILE, DATABASE_URL, ROOT_DIR
from app.services.backup_service import BackupResult, BackupService

LEGACY_BASELINE_REVISION = "0001_initial"
LEGACY_TABLES = frozenset(
    {"assets", "transactions", "price_history", "portfolio_snapshots", "alerts", "settings"}
)


class MigrationError(RuntimeError):
    """Şema güvenli biçimde yükseltilemediğinde üretilir."""


@dataclass(frozen=True)
class MigrationPlan:
    current_revision: Optional[str]
    target_revision: str
    requires_upgrade: bool
    requires_backup: bool
    is_legacy: bool = False
    is_new_database: bool = False

    @property
    def summary(self) -> str:
        if self.is_new_database:
            return "Yeni veritabanı güncel şemayla oluşturulacak."
        current = self.current_revision or "sürümsüz eski şema"
        return f"Veritabanı şeması {current} → {self.target_revision} yükseltilecek."


def alembic_config(database_url: str = DATABASE_URL) -> Config:
    # Programatik yapılandırma wheel/PyInstaller kurulumunda proje kökünde
    # ayrı bir alembic.ini dosyasına bağımlılığı ortadan kaldırır.
    config = Config()
    config.set_main_option("script_location", str(Path(ROOT_DIR) / "app/database/migrations"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    return config


class MigrationService:
    @staticmethod
    def inspect_plan(engine: Engine) -> MigrationPlan:
        config = alembic_config(str(engine.url))
        target = ScriptDirectory.from_config(config).get_current_head()
        if target is None:
            raise MigrationError("Alembic head revision bulunamadı.")

        table_names = set(inspect(engine).get_table_names())
        if not table_names:
            return MigrationPlan(None, target, True, False, is_new_database=True)

        if "alembic_version" not in table_names:
            if not LEGACY_TABLES.issubset(table_names):
                missing = ", ".join(sorted(LEGACY_TABLES.difference(table_names)))
                raise MigrationError(f"Bilinmeyen sürümsüz şema; eksik tablolar: {missing}")
            return MigrationPlan(None, target, True, True, is_legacy=True)

        with engine.connect() as connection:
            current = MigrationContext.configure(connection).get_current_revision()
        return MigrationPlan(current, target, current != target, current != target)

    @staticmethod
    def ensure_current(
        engine: Engine,
        *,
        approved: bool = False,
        backup_callback: Optional[Callable[[], BackupResult]] = None,
    ) -> MigrationPlan:
        plan = MigrationService.inspect_plan(engine)
        if not plan.requires_upgrade:
            return plan
        if plan.requires_backup and not approved:
            raise MigrationError("Şema yükseltmesi kullanıcı onayı bekliyor.")

        if plan.requires_backup:
            backup = (backup_callback or BackupService.create_backup)()
            if not backup:
                raise MigrationError("Migration öncesi güvenlik yedeği alınamadı: " + backup.error)

        config = alembic_config(str(engine.url))
        database_name = engine.url.database
        staging_path: Path | None = None
        try:
            # Var olan veritabanı doğrudan değiştirilmez. SQLite Backup API ile
            # alınan çalışma kopyası yükseltilip doğrulandıktan sonra atomik
            # olarak aktif dosyanın yerine geçirilir.
            if not plan.is_new_database and database_name not in (None, "", ":memory:"):
                database_path = Path(database_name).resolve()
                staging_path = database_path.with_suffix(database_path.suffix + ".migration.tmp")
                if staging_path.exists():
                    staging_path.unlink()
                BackupService._copy_with_sqlite_backup(database_path, staging_path)
                staging_config = alembic_config(f"sqlite:///{staging_path}")
                if plan.is_legacy:
                    command.stamp(staging_config, LEGACY_BASELINE_REVISION)
                command.upgrade(staging_config, "head")
                preview = BackupService.validate_database(staging_path)
                if not preview or preview.schema_revision != plan.target_revision:
                    detail = preview.error if not preview else "Beklenen Alembic sürümü bulunamadı."
                    raise MigrationError(f"Migration çalışma kopyası doğrulanamadı: {detail}")

                engine.dispose()
                os.replace(staging_path, database_path)
                for suffix in ("-wal", "-shm"):
                    sidecar = Path(str(database_path) + suffix)
                    if sidecar.exists():
                        sidecar.unlink()
            else:
                engine.dispose()
                command.upgrade(config, "head")
        except Exception as exc:
            if staging_path is not None and staging_path.exists():
                staging_path.unlink()
            if isinstance(exc, MigrationError):
                raise
            raise MigrationError(f"Veritabanı migration başarısız: {exc}") from exc
        return plan


def production_database_exists() -> bool:
    return Path(DATABASE_FILE).is_file()
