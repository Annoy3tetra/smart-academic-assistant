import os
import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.neighbors import NearestNeighbors

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
KB_PATH = os.path.join(BASE_DIR, "../knowledge_base/academic_content.txt")

MODEL_PATH = os.path.join(BASE_DIR, "nn_model.pkl")
CHUNKS_PATH = os.path.join(BASE_DIR, "chunks.npy")


with open(KB_PATH, "r", encoding="utf-8") as f:
    text = f.read()

chunks = [chunk.strip() for chunk in text.split("###") if chunk.strip()]

print("Chunks found:", len(chunks))

model = SentenceTransformer("all-MiniLM-L6-v2")
embeddings = model.encode(chunks)


nn = NearestNeighbors(n_neighbors=2, metric="cosine")
nn.fit(embeddings)

with open(MODEL_PATH, "wb") as f:
    pickle.dump(nn, f)

np.save(CHUNKS_PATH, chunks)

print("✅ RAG Index Built Successfully (Sklearn Version)")
