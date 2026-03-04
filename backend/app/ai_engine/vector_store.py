from pathlib import Path
from typing import Any, Sequence

import faiss
import numpy as np

from app.ai_engine.embedding_engine import embed_batch


class FaissVectorStore:
    def __init__(self, index_path: Path, chunks_path: Path):
        self.index_path = Path(index_path)
        self.chunks_path = Path(chunks_path)
        self.index: faiss.IndexFlatL2 | None = None
        self.chunks: list[str] = []

    def load(self) -> bool:
        if not self.index_path.exists() or not self.chunks_path.exists():
            return False

        self.index = faiss.read_index(str(self.index_path))
        self.chunks = np.load(str(self.chunks_path), allow_pickle=True).tolist()
        return True

    def save(self) -> None:
        if self.index is None:
            raise RuntimeError("Cannot save vector store before building or loading index.")

        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self.chunks_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self.index, str(self.index_path))
        np.save(str(self.chunks_path), np.array(self.chunks, dtype=object))

    def build(self, chunks: Sequence[str]) -> None:
        cleaned_chunks = [str(chunk).strip() for chunk in chunks if str(chunk).strip()]
        if not cleaned_chunks:
            raise ValueError("No document chunks available to build FAISS index.")

        embeddings = embed_batch(cleaned_chunks)
        if embeddings.size == 0:
            raise ValueError("Embedding generation failed for document chunks.")

        dimension = int(embeddings.shape[1])
        index = faiss.IndexFlatL2(dimension)
        index.add(embeddings)

        self.index = index
        self.chunks = cleaned_chunks
        self.save()

    def load_or_build(self, chunks: Sequence[str]) -> None:
        if self.load():
            return
        self.build(chunks)

    def search(self, query_embedding: np.ndarray, top_k: int = 3) -> list[dict[str, Any]]:
        if self.index is None:
            raise RuntimeError("FAISS index is not initialized. Call load_or_build first.")
        if not self.chunks:
            return []

        k = max(1, min(int(top_k), len(self.chunks)))
        query = np.asarray(query_embedding, dtype="float32").reshape(1, -1)
        distances, indices = self.index.search(query, k)

        results: list[dict[str, Any]] = []
        for distance, idx in zip(distances[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            results.append(
                {
                    "index": int(idx),
                    "distance": float(distance),
                    "chunk": self.chunks[idx],
                }
            )
        return results
