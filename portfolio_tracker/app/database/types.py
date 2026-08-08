"""Veritabanında kullanılan ortak SQLAlchemy veri türleri."""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import DateTime
from sqlalchemy.types import TypeDecorator


def utc_now() -> datetime:
    """Zaman dilimi bilgili güncel UTC zamanı döndürür."""
    return datetime.now(timezone.utc)


class UTCDateTime(TypeDecorator):
    """SQLite'ta UTC saklayıp Python tarafında aware datetime döndüren tür."""

    impl = DateTime
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            value = value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc).replace(tzinfo=None)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if value.tzinfo is None:
            return value.replace(tzinfo=timezone.utc)
        return value.astimezone(timezone.utc)
