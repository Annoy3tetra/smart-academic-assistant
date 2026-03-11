from fastapi import FastAPI
from app.core.database import Base,engine,get_db
from app.api.v1 import user, auth, data_store
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import AUTO_CREATE_TABLES
from app.models import user as user_models  # noqa: F401


app = FastAPI()


app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=r"^https?://(localhost|127\.0\.0\.1)(:\d+)?$",
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(user.router)
app.include_router(auth.router)
app.include_router(data_store.router)


@app.on_event("startup")
def ensure_tables():
    if not AUTO_CREATE_TABLES:
        return
    Base.metadata.create_all(bind=engine)


@app.get("/healthz")
def healthz():
    return {"ok": True}
