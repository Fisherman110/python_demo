from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query, status

from app.db.session import db
from app.dependencies import get_current_user, require_permission
from app.schemas import BookCreate, BookResponse, BookUpdate, BorrowRequest, BorrowResponse


router = APIRouter(prefix="/books", tags=["books"])
borrow_router = APIRouter(prefix="/borrows", tags=["borrows"])


def book_from_row(row) -> BookResponse:
    return BookResponse(
        id=row["id"],
        isbn=row["isbn"],
        title=row["title"],
        author=row["author"],
        publisher=row["publisher"] or "",
        category=row["category"] or "",
        total_copies=row["total_copies"],
        available_copies=row["available_copies"],
        location=row["location"] or "",
        status=row["status"],
    )


def borrow_from_row(row) -> BorrowResponse:
    return BorrowResponse(
        id=row["id"],
        user_id=row["user_id"],
        book_id=row["book_id"],
        borrowed_at=row["borrowed_at"],
        due_at=row["due_at"] or "",
        returned_at=row["returned_at"] or "",
        status=row["status"],
    )


@router.get("", response_model=list[BookResponse])
def list_books(
    q: str = Query(default=""),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    _: dict = Depends(require_permission("books:read")),
):
    keyword = q.strip()
    if keyword:
        pattern = f"%{keyword}%"
        rows = db.fetch_all(
            """
            SELECT *
            FROM books
            WHERE status != 'deleted'
              AND (title LIKE ? OR author LIKE ? OR isbn LIKE ? OR category LIKE ?)
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (pattern, pattern, pattern, pattern, limit, offset),
        )
    else:
        rows = db.fetch_all(
            """
            SELECT *
            FROM books
            WHERE status != 'deleted'
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            (limit, offset),
        )
    return [book_from_row(row) for row in rows]


@router.get("/{book_id}", response_model=BookResponse)
def get_book(book_id: int, _: dict = Depends(require_permission("books:read"))):
    row = db.fetch_one("SELECT * FROM books WHERE id = ? AND status != 'deleted'", (book_id,))
    if not row:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
    return book_from_row(row)


@router.post("", response_model=BookResponse, status_code=status.HTTP_201_CREATED)
def create_book(payload: BookCreate, _: dict = Depends(require_permission("books:write"))):
    try:
        with db.transaction(write=True) as conn:
            cursor = conn.execute(
                """
                INSERT INTO books(
                    isbn, title, author, publisher, category, total_copies, available_copies, location
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    payload.isbn,
                    payload.title,
                    payload.author,
                    payload.publisher,
                    payload.category,
                    payload.total_copies,
                    payload.total_copies,
                    payload.location,
                ),
            )
            row = conn.execute("SELECT * FROM books WHERE id = ?", (cursor.lastrowid,)).fetchone()
    except sqlite3.IntegrityError as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="ISBN already exists") from exc
    return book_from_row(row)


@router.patch("/{book_id}", response_model=BookResponse)
def update_book(book_id: int, payload: BookUpdate, _: dict = Depends(require_permission("books:write"))):
    if hasattr(payload, "model_dump"):
        values = payload.model_dump(exclude_unset=True)
    else:
        values = payload.dict(exclude_unset=True)
    if not values:
        row = db.fetch_one("SELECT * FROM books WHERE id = ? AND status != 'deleted'", (book_id,))
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        return book_from_row(row)

    allowed = {"isbn", "title", "author", "publisher", "category", "total_copies", "location", "status"}
    updates = {key: value for key, value in values.items() if key in allowed}

    with db.transaction(write=True) as conn:
        current = conn.execute("SELECT * FROM books WHERE id = ? AND status != 'deleted'", (book_id,)).fetchone()
        if not current:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")

        if "total_copies" in updates:
            borrowed = current["total_copies"] - current["available_copies"]
            if updates["total_copies"] < borrowed:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Total copies cannot be less than borrowed copies",
                )
            updates["available_copies"] = updates["total_copies"] - borrowed

        set_sql = ", ".join(f"{key} = ?" for key in updates)
        params = list(updates.values()) + [book_id]
        conn.execute(f"UPDATE books SET {set_sql}, updated_at = CURRENT_TIMESTAMP WHERE id = ?", params)
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
    return book_from_row(row)


@router.delete("/{book_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_book(book_id: int, _: dict = Depends(require_permission("books:write"))):
    with db.transaction(write=True) as conn:
        row = conn.execute("SELECT * FROM books WHERE id = ?", (book_id,)).fetchone()
        if not row:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        borrowed = row["total_copies"] - row["available_copies"]
        if borrowed > 0:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Book has active borrow records")
        conn.execute("UPDATE books SET status = 'deleted', updated_at = CURRENT_TIMESTAMP WHERE id = ?", (book_id,))


@borrow_router.post("", response_model=BorrowResponse, status_code=status.HTTP_201_CREATED)
def borrow_book(payload: BorrowRequest, user=Depends(get_current_user)):
    if "borrows:write" not in user["permissions"]:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Missing permission: borrows:write")

    with db.transaction(write=True) as conn:
        book = conn.execute(
            "SELECT * FROM books WHERE id = ? AND status = 'active'",
            (payload.book_id,),
        ).fetchone()
        if not book:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Book not found")
        if book["available_copies"] <= 0:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="No available copies")

        existing = conn.execute(
            """
            SELECT id
            FROM borrow_records
            WHERE user_id = ? AND book_id = ? AND status = 'borrowed'
            """,
            (user["id"], payload.book_id),
        ).fetchone()
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="User already borrowed this book")

        conn.execute(
            """
            UPDATE books
            SET available_copies = available_copies - 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ? AND available_copies > 0
            """,
            (payload.book_id,),
        )
        cursor = conn.execute(
            """
            INSERT INTO borrow_records(user_id, book_id, due_at)
            VALUES (?, ?, ?)
            """,
            (user["id"], payload.book_id, payload.due_at),
        )
        row = conn.execute("SELECT * FROM borrow_records WHERE id = ?", (cursor.lastrowid,)).fetchone()
    return borrow_from_row(row)


@borrow_router.post("/{borrow_id}/return", response_model=BorrowResponse)
def return_book(borrow_id: int, user=Depends(get_current_user)):
    with db.transaction(write=True) as conn:
        record = conn.execute("SELECT * FROM borrow_records WHERE id = ?", (borrow_id,)).fetchone()
        if not record:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Borrow record not found")
        if record["status"] != "borrowed":
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Borrow record already returned")
        if record["user_id"] != user["id"] and "borrows:write" not in user["permissions"]:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cannot return other user's book")

        conn.execute(
            """
            UPDATE borrow_records
            SET status = 'returned',
                returned_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (borrow_id,),
        )
        conn.execute(
            """
            UPDATE books
            SET available_copies = available_copies + 1,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (record["book_id"],),
        )
        row = conn.execute("SELECT * FROM borrow_records WHERE id = ?", (borrow_id,)).fetchone()
    return borrow_from_row(row)


@borrow_router.get("", response_model=list[BorrowResponse])
def list_borrows(
    user_id: int | None = None,
    status_filter: str = Query(default="", alias="status"),
    user=Depends(get_current_user),
):
    can_read_all = "borrows:read" in user["permissions"]
    target_user_id = user_id if can_read_all and user_id else user["id"]

    where = ["user_id = ?"]
    params = [target_user_id]
    if status_filter:
        where.append("status = ?")
        params.append(status_filter)

    rows = db.fetch_all(
        f"""
        SELECT *
        FROM borrow_records
        WHERE {' AND '.join(where)}
        ORDER BY borrowed_at DESC, id DESC
        LIMIT 200
        """,
        params,
    )
    return [borrow_from_row(row) for row in rows]
