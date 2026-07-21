from __future__ import annotations

from app.core.config import settings
from app.core.security import hash_password
from app.db.lightsql import LightSql
from app.db.schema import init_db


db = LightSql(
    settings.database_path,
    pool_size=settings.pool_size,
    busy_timeout_ms=settings.sqlite_busy_timeout_ms,
)


def initialize_database():
    init_db(db, hash_password("admin123"))


def close_database():
    db.close()
