from __future__ import annotations

import sqlite3
import threading
from contextlib import contextmanager
from pathlib import Path
from queue import Empty, LifoQueue
from typing import Any, Iterable


class LightSql:
    """Tiny SQLite storage engine wrapper tuned for local concurrent APIs.

    SQLite still serializes writes, so the design keeps transactions short,
    enables WAL for concurrent reads, and uses a bounded connection pool to
    prevent request spikes from opening unbounded file handles.
    """

    def __init__(self, db_path: Path, pool_size: int = 32, busy_timeout_ms: int = 5000):
        self.db_path = Path(db_path)
        self.pool_size = pool_size
        self.busy_timeout_ms = busy_timeout_ms
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._pool: LifoQueue[sqlite3.Connection] = LifoQueue(maxsize=pool_size)
        self._lock = threading.Lock()
        self._created = 0

    def _create_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(
            self.db_path,
            timeout=self.busy_timeout_ms / 1000,
            isolation_level=None,
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        conn.execute(f"PRAGMA busy_timeout = {self.busy_timeout_ms}")
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA synchronous = NORMAL")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA temp_store = MEMORY")
        return conn

    @contextmanager
    def connection(self):
        conn = self._checkout()
        try:
            yield conn
        finally:
            self._release(conn)

    @contextmanager
    def transaction(self, write: bool = True):
        with self.connection() as conn:
            conn.execute("BEGIN IMMEDIATE" if write else "BEGIN")
            try:
                yield conn
                conn.execute("COMMIT")
            except Exception:
                conn.execute("ROLLBACK")
                raise

    def execute(self, sql: str, params: Iterable[Any] = ()):
        with self.transaction(write=True) as conn:
            cursor = conn.execute(sql, tuple(params))
            return cursor.lastrowid, cursor.rowcount

    def fetch_one(self, sql: str, params: Iterable[Any] = ()):
        with self.connection() as conn:
            return conn.execute(sql, tuple(params)).fetchone()

    def fetch_all(self, sql: str, params: Iterable[Any] = ()):
        with self.connection() as conn:
            return conn.execute(sql, tuple(params)).fetchall()

    def executescript(self, script: str):
        with self.connection() as conn:
            conn.executescript(script)

    def close(self):
        while True:
            try:
                conn = self._pool.get_nowait()
            except Empty:
                break
            conn.close()
        with self._lock:
            self._created = 0

    def _checkout(self) -> sqlite3.Connection:
        try:
            return self._pool.get_nowait()
        except Empty:
            with self._lock:
                if self._created < self.pool_size:
                    self._created += 1
                    return self._create_connection()
            return self._pool.get()

    def _release(self, conn: sqlite3.Connection):
        try:
            self._pool.put_nowait(conn)
        except Exception:
            conn.close()
