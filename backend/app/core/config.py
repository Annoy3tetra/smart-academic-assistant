import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ENV_FILE = os.path.join(BASE_DIR, ".env")
load_dotenv(ENV_FILE)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

if not DATABASE_URL:
    raise RuntimeError(
        "DATABASE_URL is required and must point to PostgreSQL. "
        "Set it in backend/.env."
    )

if not DATABASE_URL.lower().startswith(("postgresql://", "postgresql+psycopg2://")):
    raise RuntimeError(
        "Unsupported DATABASE_URL. Use a PostgreSQL URL "
        "(postgresql:// or postgresql+psycopg2://)."
    )
