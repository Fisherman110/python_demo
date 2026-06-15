import sqlite3
from dataclasses import dataclass
from pathlib import Path


@dataclass
class PasswordRecord:
    record_id: int
    platform: str
    account: str
    username: str
    password: str
    phone: str
    email: str
    remark: str
    created_at: str
    updated_at: str


class LightSqlStore:
    """Small SQL storage wrapper for password records.

    The database is a local SQLite file. All statements use parameters to avoid
    SQL injection when users search or edit record fields.
    """

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self.connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS password_records (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    platform TEXT NOT NULL,
                    account TEXT NOT NULL,
                    username TEXT DEFAULT '',
                    password TEXT NOT NULL,
                    phone TEXT DEFAULT '',
                    email TEXT DEFAULT '',
                    remark TEXT DEFAULT '',
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
                """
            )
            self._ensure_column(conn, "username", "TEXT DEFAULT ''")
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_password_records_search
                ON password_records(platform, account, username, phone, email)
                """
            )

    @staticmethod
    def _ensure_column(conn, column_name, column_sql):
        columns = {row["name"] for row in conn.execute("PRAGMA table_info(password_records)")}
        if column_name not in columns:
            conn.execute(f"ALTER TABLE password_records ADD COLUMN {column_name} {column_sql}")

    def add_record(self, platform, account, username, password, phone="", email="", remark=""):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                INSERT INTO password_records(platform, account, username, password, phone, email, remark)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (platform, account, username, password, phone, email, remark),
            )
            return cursor.lastrowid

    def update_record(self, record_id, platform, account, username, password, phone="", email="", remark=""):
        with self.connect() as conn:
            cursor = conn.execute(
                """
                UPDATE password_records
                SET platform = ?,
                    account = ?,
                    username = ?,
                    password = ?,
                    phone = ?,
                    email = ?,
                    remark = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (platform, account, username, password, phone, email, remark, record_id),
            )
            return cursor.rowcount > 0

    def delete_record(self, record_id):
        with self.connect() as conn:
            cursor = conn.execute("DELETE FROM password_records WHERE id = ?", (record_id,))
            return cursor.rowcount > 0

    def search_records(self, keyword=""):
        keyword = keyword.strip()
        params = []
        where_sql = ""

        if keyword:
            pattern = f"%{keyword}%"
            where_sql = """
                WHERE platform LIKE ?
                   OR account LIKE ?
                   OR username LIKE ?
                   OR phone LIKE ?
                   OR email LIKE ?
                   OR remark LIKE ?
            """
            params = [pattern, pattern, pattern, pattern, pattern, pattern]

        with self.connect() as conn:
            rows = conn.execute(
                f"""
                SELECT id, platform, account, username, password, phone, email, remark, created_at, updated_at
                FROM password_records
                {where_sql}
                ORDER BY updated_at DESC, id DESC
                """,
                params,
            ).fetchall()

        return [self._row_to_record(row) for row in rows]

    @staticmethod
    def _row_to_record(row):
        return PasswordRecord(
            record_id=row["id"],
            platform=row["platform"],
            account=row["account"],
            username=row["username"] or "",
            password=row["password"],
            phone=row["phone"] or "",
            email=row["email"] or "",
            remark=row["remark"] or "",
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )
