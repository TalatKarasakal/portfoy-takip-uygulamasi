"""Uygulama açılışında güvenli Alembic migration yönetimi."""

from __future__ import annotations

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
    config = Config(str(Path(ROOT_DIR) / "alembic.ini"))
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
        try:
            engine.dispose()
            if plan.is_legacy:
                command.stamp(config, LEGACY_BASELINE_REVISION)
            command.upgrade(config, "head")
        except Exception as exc:
            raise MigrationError(f"Veritabanı migration başarısız: {exc}") from exc
        return plan


def production_database_exists() -> bool:
    return Path(DATABASE_FILE).is_file()
