from __future__ import annotations

from pydantic import BaseModel, Field


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class LoginRequest(BaseModel):
    username: str = Field(min_length=3, max_length=64)
    password: str = Field(min_length=6, max_length=128)


class RegisterRequest(LoginRequest):
    display_name: str = ""
    email: str = ""
    phone: str = ""


class UserResponse(BaseModel):
    id: int
    username: str
    display_name: str
    email: str
    phone: str
    is_active: bool
    roles: list[str]
    permissions: list[str]


class AssignRoleRequest(BaseModel):
    role: str


class BookCreate(BaseModel):
    isbn: str = Field(min_length=3, max_length=64)
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=120)
    publisher: str = ""
    category: str = ""
    total_copies: int = Field(default=1, ge=0)
    location: str = ""


class BookUpdate(BaseModel):
    isbn: str | None = None
    title: str | None = None
    author: str | None = None
    publisher: str | None = None
    category: str | None = None
    total_copies: int | None = Field(default=None, ge=0)
    location: str | None = None
    status: str | None = None


class BookResponse(BaseModel):
    id: int
    isbn: str
    title: str
    author: str
    publisher: str
    category: str
    total_copies: int
    available_copies: int
    location: str
    status: str


class BorrowRequest(BaseModel):
    book_id: int
    due_at: str = ""


class BorrowResponse(BaseModel):
    id: int
    user_id: int
    book_id: int
    borrowed_at: str
    due_at: str
    returned_at: str
    status: str
