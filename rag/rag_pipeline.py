from rag.qa import rag_answer_from_chunks
from rag.retrieval import retrieve_chunks_for_chat


def rag_answer(
    *,
    question: str,
    document=None,
):
    """
    HIGH-LEVEL RAG ANSWER.
    Used by chat, API, future features.
    Returns MARKDOWN.
    """

    # 1️⃣ Retrieve grounded chunks
    chunks = retrieve_chunks_for_chat(
        user=document.owner if document else None,
        question=question,
        document=document,
        max_chunks=8,
    )

    # 2️⃣ Delegate answering (single source of truth)
    answer_md = rag_answer_from_chunks(
        question=question,
        chunks=chunks,
    )

    return answer_md
