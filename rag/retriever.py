import numpy as np
from django.db.models import Q

from .embeddings import embed_texts
from .faiss_utils import load_or_create_index
from documents.models import Document


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
    - Global mode: no context provided (auto-search all accessible docs)
    """

    # -----------------------------------------------------
    # 🔹 Embed Query
    # -----------------------------------------------------
    query_embedding = embed_texts([query])[0]
    results = []

    # -----------------------------------------------------
    # 🔐 Accessible Documents
    # -----------------------------------------------------
    docs_qs = Document.objects.filter(
        Q(is_public=True) | Q(uploaded_by=user)
    )

    if public_only:
        docs_qs = docs_qs.filter(is_public=True)

    if document_ids:
        docs_qs = docs_qs.filter(id__in=document_ids)

    if folder_ids:
        docs_qs = docs_qs.filter(folder_id__in=folder_ids)

    # Optional: limit number of docs searched (scalability)
    docs_qs = docs_qs[:30]

    # -----------------------------------------------------
    # 🔍 Search Each Document Index
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

        for rank, idx in enumerate(I[0]):
            if idx < len(chunks):
                results.append({
                    "text": chunks[idx],
                    "document_id": doc.id,
                    "document_title": doc.title,
                    "score": float(D[0][rank]),  # Lower = better (L2 distance)
                })

    # -----------------------------------------------------
    # 🔝 Global Ranking
    # -----------------------------------------------------
    results.sort(key=lambda x: x["score"])

    # -----------------------------------------------------
    # 🔀 Ensure Document Diversity
    # (Prevents one large doc dominating results)
    # -----------------------------------------------------
    final_results = []
    seen_docs = set()

    for r in results:
        if (
            r["document_id"] not in seen_docs
            or len(final_results) < k
        ):
            final_results.append(r)
            seen_docs.add(r["document_id"])

        if len(final_results) >= k:
            break

    return final_results


# =========================================================
# 🔹 TEXT-ONLY HELPER (Backward Compatibility)
# =========================================================
def retrieve_chunk_texts(**kwargs):
    """
    Returns only chunk text.
    Useful for simple RAG pipelines.
    """
    return [r["text"] for r in retrieve_chunks(**kwargs)]