from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, status

from app.core.config import settings
from app.core.security import create_access_token, hash_password, verify_password
from app.db.session import db
from app.dependencies import get_current_user, load_user, require_permission
from app.schemas import AssignRoleRequest, LoginRequest, RegisterRequest, TokenResponse, UserResponse


router = APIRouter(prefix="/auth", tags=["auth"])
users_router = APIRouter(prefix="/users", tags=["users"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def register(payload: RegisterRequest):
    password_hash = hash_password(payload.password)
    try:
        with db.transaction(write=True) as conn:
            cursor = conn.execute(
                """
                INSERT INTO users(username, password_hash, display_name, email, phone)
                VALUES (?, ?, ?, ?, ?)
                """,
                (payload.username, password_hash, payload.display_name, payload.email, payload.phone),
            )
            user_id = cursor.lastrowid
            member_role = conn.execute("SELECT id FROM roles WHERE name = 'member'").fetchone()
            conn.execute("INSERT INTO user_roles(user_id, role_id) VALUES (?, ?)", (user_id, member_role["id"]))
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Username already exists") from exc

    return UserResponse(**load_user(user_id))


@router.post("/login", response_model=TokenResponse)
def login(payload: LoginRequest):
    row = db.fetch_one(
        "SELECT id, username, password_hash, is_active FROM users WHERE username = ?",
        (payload.username,),
    )
    if not row or not bool(row["is_active"]) or not verify_password(payload.password, row["password_hash"]):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid username or password")

    token = create_access_token(str(row["id"]), {"username": row["username"]})
    return TokenResponse(access_token=token, expires_in=settings.access_token_ttl_seconds)


@router.get("/me", response_model=UserResponse)
def me(user=Depends(get_current_user)):
    return UserResponse(**user)


@users_router.get("", response_model=list[UserResponse])
def list_users(_: dict = Depends(require_permission("users:read"))):
    rows = db.fetch_all("SELECT id FROM users ORDER BY id DESC")
    return [UserResponse(**load_user(row["id"])) for row in rows]


@users_router.post("/{user_id}/roles", response_model=UserResponse)
def assign_role(user_id: int, payload: AssignRoleRequest, _: dict = Depends(require_permission("users:write"))):
    with db.transaction(write=True) as conn:
        user_row = conn.execute("SELECT id FROM users WHERE id = ?", (user_id,)).fetchone()
        role_row = conn.execute("SELECT id FROM roles WHERE name = ?", (payload.role,)).fetchone()
        if not user_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if not role_row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Role not found")
        conn.execute(
            "INSERT OR IGNORE INTO user_roles(user_id, role_id) VALUES (?, ?)",
            (user_id, role_row["id"]),
        )
    return UserResponse(**load_user(user_id))
