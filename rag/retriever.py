from django.db.models import Q
from pgvector.django import L2Distance

from documents.models import Document, DocumentChunk
from .embeddings import embed_texts


# =========================================================
# 🔹 CORE RETRIEVER (Postgres + pgvector)
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
    Semantic retrieval using pgvector (PostgreSQL).

    Modes:
    - Context mode: document_ids or folder_ids provided
    - Global mode: no context provided (auto-search all accessible docs)
    """

    # -----------------------------------------------------
    # 🔹 Embed Query
    # -----------------------------------------------------
    query_embedding = embed_texts([query])[0]

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
    docs_qs = docs_qs[:50]

    # -----------------------------------------------------
    # 🔍 Vector Similarity Search (Across Chunks)
    # -----------------------------------------------------
    chunks = (
        DocumentChunk.objects
        .filter(document__in=docs_qs)
        .annotate(distance=L2Distance("embedding", query_embedding))
        .order_by("distance")[:k]
    )

    # -----------------------------------------------------
    # 🔁 Format Results
    # -----------------------------------------------------
    results = [
        {
            "text": chunk.content,
            "document_id": chunk.document.id,
            "document_title": chunk.document.display_name,
            "score": float(chunk.distance),  # Lower = better
        }
        for chunk in chunks
    ]

    return results


# =========================================================
# 🔹 TEXT-ONLY HELPER
# =========================================================
def retrieve_chunk_texts(**kwargs):
    """
    Returns only chunk text.
    Useful for simple RAG pipelines.
    """
    return [r["text"] for r in retrieve_chunks(**kwargs)]