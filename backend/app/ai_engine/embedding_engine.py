from functools import lru_cache

import numpy as np
from sentence_transformers import SentenceTransformer


MODEL_NAME = "all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(MODEL_NAME)


def embed_text(text: str) -> np.ndarray:
    cleaned = text.strip()
    if not cleaned:
        dimension = _get_model().get_sentence_embedding_dimension()
        return np.zeros((dimension,), dtype="float32")

    vector = _get_model().encode(
        [cleaned],
        convert_to_numpy=True,
        show_progress_bar=False,
    )[0]
    return np.asarray(vector, dtype="float32")


def embed_batch(texts: list[str]) -> np.ndarray:
    cleaned = [str(text or "").strip() for text in texts if str(text or "").strip()]
    if not cleaned:
        dimension = _get_model().get_sentence_embedding_dimension()
        return np.empty((0, dimension), dtype="float32")

    vectors = _get_model().encode(
        cleaned,
        convert_to_numpy=True,
        show_progress_bar=False,
    )
    return np.asarray(vectors, dtype="float32")
