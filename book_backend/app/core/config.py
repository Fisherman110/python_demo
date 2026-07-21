from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]


@dataclass(frozen=True)
class Settings:
    app_name: str = "Book Management Backend"
    data_dir: Path = BASE_DIR / "data"
    database_path: Path = BASE_DIR / "data" / "library.db"
    token_secret: str = os.getenv("BOOK_BACKEND_TOKEN_SECRET", "dev-secret-change-me")
    access_token_ttl_seconds: int = int(os.getenv("BOOK_BACKEND_TOKEN_TTL", "7200"))
    pool_size: int = int(os.getenv("BOOK_BACKEND_DB_POOL_SIZE", "32"))
    sqlite_busy_timeout_ms: int = int(os.getenv("BOOK_BACKEND_SQLITE_BUSY_TIMEOUT_MS", "5000"))


settings = Settings()
