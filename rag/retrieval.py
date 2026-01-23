from django.db.models import Q
from documents.models import Document


def retrieve_chunks_for_chat(
    *,
    user,
    question,
    document=None,
    max_chunks=6,
    chunk_size=800,
):
    """
    In-memory RAG chunking using Document.extracted_text
    with STRICT access control.
    """

    # =========================
    # 🔒 ACCESS CONTROL (CRITICAL)
    # =========================
    if not document:
        return []

    allowed = Document.objects.filter(
        Q(id=document.id),
        Q(owner=user) | Q(is_public=True)
    ).exists()

    if not allowed:
        return []  # HARD STOP — prevents leaks

    if not document.extracted_text:
        return []

    # =========================
    # 🧠 CHUNKING
    # =========================
    text = document.extracted_text
    words = text.split()

    chunks = []
    start = 0

    while start < len(words) and len(chunks) < max_chunks:
        end = start + chunk_size
        chunk_text = " ".join(words[start:end])

        # Basic relevance filter
        if any(w.lower() in chunk_text.lower() for w in question.split()):
            chunks.append({
                "text": chunk_text,
                "document_title": document.title,
            })

        start = end

    return chunks
