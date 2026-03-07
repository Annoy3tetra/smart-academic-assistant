import os
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_ROOT = BACKEND_DIR.parent
ENV_FILE = BACKEND_DIR / ".env"
load_dotenv(ENV_FILE)

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()


def _normalize_database_url(raw_url: str) -> str:
    url = str(raw_url or "").strip()

    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    if not url:
        return url

    parsed = urlparse(url)
    query = dict(parse_qsl(parsed.query, keep_blank_values=True))

    host = (parsed.hostname or "").strip().lower()
    is_local = host in {"localhost", "127.0.0.1"} or host.endswith(".local")

    # Managed cloud Postgres providers generally require TLS in production.
    if not is_local and "sslmode" not in query:
        query["sslmode"] = os.getenv("DB_SSLMODE", "require").strip() or "require"

    if "connect_timeout" not in query:
        query["connect_timeout"] = os.getenv("DB_CONNECT_TIMEOUT", "10").strip() or "10"

    normalized_query = urlencode(query)
    return urlunparse(parsed._replace(query=normalized_query))


DATABASE_URL = _normalize_database_url(DATABASE_URL)

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


def _resolve_path(raw_path: str, base_dir: Path) -> Path:
    path = Path(raw_path)
    if path.is_absolute():
        return path
    return (base_dir / path).resolve()


USE_LLM = os.getenv("USE_LLM", "false").lower() == "true"
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "false").lower() == "true"
RAG_TOP_K = int(os.getenv("RAG_TOP_K", "3"))

RAG_DATA_DIR = _resolve_path(
    os.getenv("RAG_DATA_DIR", "backend/app/ai_engine/data"),
    PROJECT_ROOT,
)
RAG_INDEX_PATH = RAG_DATA_DIR / "faiss_index.bin"
RAG_CHUNKS_PATH = RAG_DATA_DIR / "faiss_chunks.npy"

RAG_SOURCE_FILE = _resolve_path(
    os.getenv("RAG_SOURCE_FILE", "RAG MODEL/ml/knowledge_base/academic_content.txt"),
    PROJECT_ROOT,
)

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://localhost:11434/api/generate").strip()
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "phi3").strip() or "phi3"
