import logging
import os

from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from fastapi import FastAPI, Response
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import user, auth, data_store
from app.core.config import AUTO_CREATE_TABLES
from app.core.database import Base, engine
from app.models import user as user_models  # noqa: F401


logger = logging.getLogger(__name__)


app = FastAPI()

_DEFAULT_ORIGINS = [
    "https://smart-academic-assistant-lilac.vercel.app",
    "http://localhost:5500",
    "http://127.0.0.1:5500",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
]

_extra = os.getenv("ALLOWED_ORIGINS", "")
ALLOWED_ORIGINS = [
    o.strip() for o in (_extra.split(",") if _extra.strip() else [])
] or _DEFAULT_ORIGINS

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(data_store.router)


def _database_startup_hint(err: Exception) -> str | None:
    msg = str(getattr(err, "orig", err) or "").lower()
    if "network is unreachable" in msg and "supabase.co" in msg:
        return (
            "Render could not reach the direct Supabase database host. "
            "Use the Supavisor pooler/IPv4 connection string for DATABASE_URL."
        )
    if "connection refused" in msg or "timeout expired" in msg:
        return "Verify DATABASE_URL, SSL settings, and whether the PostgreSQL host is reachable from Render."
    return None


@app.on_event("startup")
def ensure_tables():
    app.state.db_ready = True
    app.state.db_error = None

    if not AUTO_CREATE_TABLES:
        logger.info("AUTO_CREATE_TABLES disabled; skipping startup schema sync.")
        return

    try:
        Base.metadata.create_all(bind=engine)
    except SQLAlchemyError as err:
        app.state.db_ready = False
        app.state.db_error = str(getattr(err, "orig", err) or err)
        logger.exception(
            "Database schema sync failed during startup. Continuing without confirmed DB connectivity."
        )
        hint = _database_startup_hint(err)
        if hint:
            logger.error(hint)


@app.get("/healthz")
def healthz():
    return {
        "ok": True,
        "database": "ready" if getattr(app.state, "db_ready", True) else "unavailable",
    }


@app.get("/readyz")
def readyz(response: Response):
    db_ready = getattr(app.state, "db_ready", True)
    if not db_ready:
        response.status_code = 503
    return {
        "ok": db_ready,
        "database": "ready" if db_ready else "unavailable",
    }


if __name__ == "__main__":
    try:
        port = int(os.getenv("PORT", "10000"))
    except ValueError:
        port = 10000
    uvicorn.run("app.main:app", host="0.0.0.0", port=port)
