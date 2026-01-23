import numpy as np
from django.db.models import Q

from .embeddings import embed_texts
from .faiss_utils import load_or_create_index
from documents.models import Document


# =========================================================
# 🔹 TEXT CHUNKING
# =========================================================
def chunk_text(text, size=500, overlap=50):
    words = text.split()
    chunks = []

    step = size - overlap
    for i in range(0, len(words), step):
        chunks.append(" ".join(words[i:i + size]))

    return chunks


# =========================================================
# 🔹 CORE RETRIEVER (GLOBAL + CONTEXT MODE)
# =========================================================
def retrieve_chunks(
    user,
    query,
    k=5,
    document_ids=None,
    folder_ids=None,
    public_only=False,
):
    """
    Semantic retrieval with FAISS.

    Modes:
    - Context mode: document_ids or folder_ids provided
    - Global mode: no context provided
    """

    query_embedding = embed_texts([query])[0]
    results = []

    # -----------------------------------------------------
    # 🔐 ACCESSIBLE DOCUMENTS
    # -----------------------------------------------------
    docs_qs = Document.objects.filter(
        Q(is_public=True) | Q(owner=user)
    )

    # Basic users → public only
    if public_only:
        docs_qs = docs_qs.filter(is_public=True)

    # Context filters
    if document_ids:
        docs_qs = docs_qs.filter(id__in=document_ids)

    if folder_ids:
        docs_qs = docs_qs.filter(folder_id__in=folder_ids)

    # -----------------------------------------------------
    # 🔍 FAISS SEARCH PER DOCUMENT
    # -----------------------------------------------------
    for doc in docs_qs:
        index_name = f"doc_{doc.id}"
        index, chunks = load_or_create_index(index_name)

        if index.ntotal == 0:
            continue

        D, I = index.search(
            np.array([query_embedding]),
            min(k, index.ntotal)
        )

        for i in I[0]:
            if i < len(chunks):
                results.append({
                    "text": chunks[i],
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "score": float(D[0][list(I[0]).index(i)]),
                })

    # -----------------------------------------------------
    # 🔝 SORT + LIMIT
    # -----------------------------------------------------
    results.sort(key=lambda x: x["score"])
    return results[:k]


# =========================================================
# 🔹 SIMPLE HELPER (TEXT-ONLY, BACKWARD COMPATIBLE)
# =========================================================
def retrieve_chunk_texts(**kwargs):
    """
    Returns only chunk text (for older code compatibility)
    """
    return [r["text"] for r in retrieve_chunks(**kwargs)]
