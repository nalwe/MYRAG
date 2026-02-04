import faiss
import os
import pickle
import numpy as np
from django.conf import settings


def get_index_paths(name):
    base = os.path.join(settings.FAISS_INDEX_DIR, name)
    return (
        os.path.join(base, "index.faiss"),
        os.path.join(base, "chunks.pkl"),
        base
    )

def load_or_create_index(name):
    index_path, chunks_path, base = get_index_paths(name)
    os.makedirs(base, exist_ok=True)

    if os.path.exists(index_path):
        index = faiss.read_index(index_path)
        with open(chunks_path, "rb") as f:
            chunks = pickle.load(f)
    else:
        index = faiss.IndexFlatL2(settings.EMBEDDING_DIM)
        chunks = []

    return index, chunks

def save_index(name, index, chunks):
    index_path, chunks_path, _ = get_index_paths(name)
    faiss.write_index(index, index_path)
    with open(chunks_path, "wb") as f:
        pickle.dump(chunks, f)



FAISS_INDEX_DIR = settings.FAISS_INDEX_DIR


def get_faiss_indexes(user, scope):
    """
    Returns a list of FAISS index paths based on chat scope.
    """
    if scope == "my":
        return [FAISS_INDEX_DIR / f"user_{user.id}"]

    if scope == "public":
        return [FAISS_INDEX_DIR / "public"]

    if scope == "both":
        return [
            FAISS_INDEX_DIR / f"user_{user.id}",
            FAISS_INDEX_DIR / "public",
        ]

    # Fallback (safe default)
    return [FAISS_INDEX_DIR / "public"]

