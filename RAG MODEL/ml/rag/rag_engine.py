import os
import pickle
import io
import contextlib
import numpy as np
from sentence_transformers import SentenceTransformer
from google import genai
from google.genai.errors import APIError

# ==============================
# Paths
# ==============================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, "nn_model.pkl")
CHUNKS_PATH = os.path.join(BASE_DIR, "chunks.npy")
PROJECT_ROOT = os.path.dirname(os.path.dirname(BASE_DIR))


def _load_env_file():
    """Load KEY=VALUE pairs from common .env locations if present."""
    env_paths = [
        os.path.join(PROJECT_ROOT, ".env"),
        os.path.join(BASE_DIR, ".env"),
        os.path.join(os.getcwd(), ".env"),
    ]

    for env_path in env_paths:
        if not os.path.exists(env_path):
            continue
        with open(env_path, "r", encoding="utf-8") as f:
            for raw_line in f:
                line = raw_line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, value = line.split("=", 1)
                key = key.strip()
                value = value.strip().strip("'").strip('"')
                if key and key not in os.environ:
                    os.environ[key] = value


_load_env_file()

# Keep huggingface/transformers logs minimal in terminal runs.
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TRANSFORMERS_VERBOSITY", "error")

# ==============================
# Load Vector Model + Chunks
# ==============================

with open(MODEL_PATH, "rb") as f:
    nn_model = pickle.load(f)

chunks = np.load(CHUNKS_PATH, allow_pickle=True)


def _create_embedder():
    # Prefer cached local model to avoid HF unauthenticated network warnings.
    for local_only in (True, False):
        try:
            with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                return SentenceTransformer("all-MiniLM-L6-v2", local_files_only=local_only)
        except Exception:
            if local_only:
                continue
            raise


embedder = _create_embedder()

# ==============================
# Retrieval Layer
# ==============================

def retrieve_context(query, top_k=1):
    query_embedding = embedder.encode([query])
    distances, indices = nn_model.kneighbors(query_embedding, n_neighbors=top_k)
    retrieved_chunks = [chunks[i] for i in indices[0]]
    return "\n\n".join(retrieved_chunks)

# ==============================
# Full RAG Pipeline
# ==============================

def generate_answer(query):

    # Create Gemini client INSIDE function

    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        return (
            "Missing Gemini API key. Set GEMINI_API_KEY (or GOOGLE_API_KEY) "
            f"in your environment or .env file at {PROJECT_ROOT}\\.env and try again."
        )

    client = genai.Client(api_key=api_key)

    context = retrieve_context(query)

    prompt = f"""
    You are a programming tutor.

    Using ONLY the context provided below, teach the concept clearly.

    Context:
    {context}

    Student Question:
    {query}

    Provide:
    1. Clear Explanation
    2. Simple Example
    3. Short Summary

    Do not mention missing context.
    If the concept is found in the context, explain it directly.
    If the concept is not found, say "The provided context does not cover this topic."
    """


    models_to_try = [
        os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        "gemini-2.5-flash",
        "gemini-1.5-flash",
    ]

    last_error = None
    for model_name in dict.fromkeys(models_to_try):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt
            )
            return getattr(response, "text", "") or "No response text returned."
        except APIError as err:
            last_error = err
            status_code = getattr(err, "status_code", None)
            if status_code == 429:
                continue
            return f"Gemini API request failed: {err}"
        except Exception as err:
            return f"Unexpected error while generating answer: {err}"

    return (
        "Gemini quota exhausted for all configured models. "
        "Please wait and retry, or switch to a billed project/API key. "
        f"Last error: {last_error}"
    )
