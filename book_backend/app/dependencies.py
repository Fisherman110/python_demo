from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.security import decode_access_token
from app.db.session import db


bearer_scheme = HTTPBearer(auto_error=False)


def load_user(user_id: int):
    row = db.fetch_one(
        """
        SELECT id, username, display_name, email, phone, is_active
        FROM users
        WHERE id = ?
        """,
        (user_id,),
    )
    if not row:
        return None

    roles = db.fetch_all(
        """
        SELECT r.name
        FROM roles r
        JOIN user_roles ur ON ur.role_id = r.id
        WHERE ur.user_id = ?
        ORDER BY r.name
        """,
        (user_id,),
    )
    permissions = db.fetch_all(
        """
        SELECT DISTINCT p.code
        FROM permissions p
        JOIN role_permissions rp ON rp.permission_id = p.id
        JOIN user_roles ur ON ur.role_id = rp.role_id
        WHERE ur.user_id = ?
        ORDER BY p.code
        """,
        (user_id,),
    )
    return {
        "id": row["id"],
        "username": row["username"],
        "display_name": row["display_name"] or "",
        "email": row["email"] or "",
        "phone": row["phone"] or "",
        "is_active": bool(row["is_active"]),
        "roles": [item["name"] for item in roles],
        "permissions": [item["code"] for item in permissions],
    }


def get_current_user(credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)):
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")
    try:
        payload = decode_access_token(credentials.credentials)
        user_id = int(payload["sub"])
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token") from exc

    user = load_user(user_id)
    if not user or not user["is_active"]:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User is inactive or not found")
    return user


def require_permission(permission: str):
    def checker(user=Depends(get_current_user)):
        if permission not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing permission: {permission}")
        return user

    return checker


def request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID", "")
