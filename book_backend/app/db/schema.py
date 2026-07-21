from __future__ import annotations

from app.db.lightsql import LightSql


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    display_name TEXT DEFAULT '',
    email TEXT DEFAULT '',
    phone TEXT DEFAULT '',
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS roles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS permissions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    code TEXT NOT NULL UNIQUE,
    description TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS role_permissions (
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id INTEGER NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY(role_id, permission_id)
);

CREATE TABLE IF NOT EXISTS user_roles (
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id INTEGER NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    PRIMARY KEY(user_id, role_id)
);

CREATE TABLE IF NOT EXISTS books (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    isbn TEXT NOT NULL UNIQUE,
    title TEXT NOT NULL,
    author TEXT NOT NULL,
    publisher TEXT DEFAULT '',
    category TEXT DEFAULT '',
    total_copies INTEGER NOT NULL DEFAULT 1 CHECK(total_copies >= 0),
    available_copies INTEGER NOT NULL DEFAULT 1 CHECK(available_copies >= 0),
    location TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'active',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK(available_copies <= total_copies)
);

CREATE TABLE IF NOT EXISTS borrow_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL REFERENCES users(id),
    book_id INTEGER NOT NULL REFERENCES books(id),
    borrowed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    due_at TEXT DEFAULT '',
    returned_at TEXT DEFAULT '',
    status TEXT NOT NULL DEFAULT 'borrowed'
);

CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
CREATE INDEX IF NOT EXISTS idx_books_search ON books(title, author, isbn, category);
CREATE INDEX IF NOT EXISTS idx_books_status ON books(status, available_copies);
CREATE INDEX IF NOT EXISTS idx_borrow_user_status ON borrow_records(user_id, status);
CREATE INDEX IF NOT EXISTS idx_borrow_book_status ON borrow_records(book_id, status);
"""


ROLES = {
    "admin": "系统管理员，拥有全部权限",
    "librarian": "图书管理员，可管理图书和借还",
    "member": "普通读者，可查询图书和借还自己的图书",
}

PERMISSIONS = {
    "users:read": "查看用户",
    "users:write": "管理用户和角色",
    "books:read": "查询图书",
    "books:write": "新增、修改、删除图书",
    "borrows:read": "查询借阅记录",
    "borrows:write": "办理借书和还书",
}

ROLE_PERMISSION_MAP = {
    "admin": set(PERMISSIONS),
    "librarian": {"books:read", "books:write", "borrows:read", "borrows:write"},
    "member": {"books:read", "borrows:write"},
}


def init_db(db: LightSql, password_hash: str):
    db.executescript(SCHEMA_SQL)
    seed_roles_and_permissions(db)
    seed_admin(db, password_hash)
    seed_books(db)


def seed_roles_and_permissions(db: LightSql):
    with db.transaction(write=True) as conn:
        for role, description in ROLES.items():
            conn.execute("INSERT OR IGNORE INTO roles(name, description) VALUES (?, ?)", (role, description))
        for code, description in PERMISSIONS.items():
            conn.execute("INSERT OR IGNORE INTO permissions(code, description) VALUES (?, ?)", (code, description))

        role_rows = {row["name"]: row["id"] for row in conn.execute("SELECT id, name FROM roles").fetchall()}
        perm_rows = {row["code"]: row["id"] for row in conn.execute("SELECT id, code FROM permissions").fetchall()}
        for role, permission_codes in ROLE_PERMISSION_MAP.items():
            for code in permission_codes:
                conn.execute(
                    "INSERT OR IGNORE INTO role_permissions(role_id, permission_id) VALUES (?, ?)",
                    (role_rows[role], perm_rows[code]),
                )


def seed_admin(db: LightSql, password_hash: str):
    with db.transaction(write=True) as conn:
        conn.execute(
            """
            INSERT OR IGNORE INTO users(username, password_hash, display_name, email)
            VALUES ('admin', ?, '系统管理员', 'admin@example.local')
            """,
            (password_hash,),
        )
        admin_id = conn.execute("SELECT id FROM users WHERE username = 'admin'").fetchone()["id"]
        admin_role_id = conn.execute("SELECT id FROM roles WHERE name = 'admin'").fetchone()["id"]
        conn.execute(
            "INSERT OR IGNORE INTO user_roles(user_id, role_id) VALUES (?, ?)",
            (admin_id, admin_role_id),
        )


def seed_books(db: LightSql):
    books = [
        ("9787111128069", "深入理解计算机系统", "Randal E. Bryant", "机械工业出版社", "计算机", 5, "A-01"),
        ("9787115546081", "Python 编程：从入门到实践", "Eric Matthes", "人民邮电出版社", "编程", 8, "A-02"),
        ("9780132350884", "代码整洁之道", "Robert C. Martin", "Prentice Hall", "软件工程", 4, "B-01"),
    ]
    with db.transaction(write=True) as conn:
        for isbn, title, author, publisher, category, copies, location in books:
            conn.execute(
                """
                INSERT OR IGNORE INTO books(
                    isbn, title, author, publisher, category, total_copies, available_copies, location
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (isbn, title, author, publisher, category, copies, copies, location),
            )
