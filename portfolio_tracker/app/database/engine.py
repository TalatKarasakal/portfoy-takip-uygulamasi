"""SQLAlchemy engine ve uygulama şema başlangıcı."""

from __future__ import annotations

from sqlalchemy import create_engine, event

from app.config import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    echo=False,
    connect_args={"check_same_thread": False, "timeout": 5.0},
)


@event.listens_for(engine, "connect")
def _configure_sqlite_connection(dbapi_connection, _connection_record) -> None:
    cursor = dbapi_connection.cursor()
    try:
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute("PRAGMA busy_timeout=5000")
    finally:
        cursor.close()


def init_db(*, migration_approved: bool = False):
    """Şemayı create_all yerine sürümlü Alembic migration ile hazırlar."""
    from app.database.migration_service import MigrationService

    return MigrationService.ensure_current(engine, approved=migration_approved)
