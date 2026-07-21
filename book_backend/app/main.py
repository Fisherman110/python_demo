from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app import __version__
from app.api.auth import router as auth_router
from app.api.auth import users_router
from app.api.books import borrow_router, router as books_router
from app.core.config import settings
from app.db.session import close_database, initialize_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    initialize_database()
    yield
    close_database()


app = FastAPI(
    title=settings.app_name,
    version=__version__,
    lifespan=lifespan,
)

app.include_router(auth_router, prefix="/api/v1")
app.include_router(users_router, prefix="/api/v1")
app.include_router(books_router, prefix="/api/v1")
app.include_router(borrow_router, prefix="/api/v1")


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__}
