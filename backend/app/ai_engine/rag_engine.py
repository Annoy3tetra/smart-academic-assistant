from functools import lru_cache
from pathlib import Path

from app.ai_engine.embedding_engine import embed_text
from app.ai_engine.llm_engine import generate_with_phi3
from app.ai_engine.vector_store import FaissVectorStore
from app.core.config import (
    RAG_CHUNKS_PATH,
    RAG_INDEX_PATH,
    RAG_SOURCE_FILE,
    RAG_TOP_K,
    USE_LLM,
)


def _split_text_into_chunks(text: str) -> list[str]:
    if "###" in text:
        chunks = [chunk.strip() for chunk in text.split("###") if chunk.strip()]
        if chunks:
            return chunks

    paragraphs = [paragraph.strip() for paragraph in text.split("\n\n") if paragraph.strip()]
    if paragraphs:
        return paragraphs

    single_line = text.strip()
    return [single_line] if single_line else []


def _load_source_chunks(source_file: Path) -> list[str]:
    if not source_file.exists():
        raise FileNotFoundError(f"Knowledge base file not found: {source_file}")

    raw_text = source_file.read_text(encoding="utf-8")
    chunks = _split_text_into_chunks(raw_text)
    if not chunks:
        raise ValueError(f"No chunks found in knowledge base file: {source_file}")
    return chunks


def _build_prompt(query: str, context_chunks: list[str]) -> str:
    context = "\n\n".join(context_chunks)
    return (
        "You are a helpful academic assistant.\n"
        "Answer the student query using only the provided context.\n"
        "If the context does not contain the answer, say exactly: "
        "\"The provided context does not cover this topic.\"\n\n"
        f"Context:\n{context}\n\n"
        f"Student query:\n{query}\n\n"
        "Answer:"
    )


@lru_cache(maxsize=1)
def _get_vector_store() -> FaissVectorStore:
    store = FaissVectorStore(index_path=RAG_INDEX_PATH, chunks_path=RAG_CHUNKS_PATH)

    if not store.load():
        raise RuntimeError(
            "FAISS index not found. Build the index locally before deploying."
        )

    return store


def generate_answer(query: str, top_k: int = RAG_TOP_K) -> str:
    cleaned_query = query.strip()
    if not cleaned_query:
        raise ValueError("Query cannot be empty.")

    vector_store = _get_vector_store()
    query_embedding = embed_text(cleaned_query)
    results = vector_store.search(query_embedding, top_k=top_k)
    if not results:
        return "No relevant context found."

    context_chunks = [item["chunk"] for item in results]

    if not USE_LLM:
        return context_chunks[0]

    prompt = _build_prompt(cleaned_query, context_chunks)
    return generate_with_phi3(prompt)


def get_rag_diagnostics() -> dict:
    vector_store = _get_vector_store()
    return {
        "use_llm": USE_LLM,
        "index_path": str(RAG_INDEX_PATH),
        "chunks_path": str(RAG_CHUNKS_PATH),
        "source_file": str(RAG_SOURCE_FILE),
        "indexed_chunks": len(vector_store.chunks),
    }
