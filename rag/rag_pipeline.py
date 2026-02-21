from rag.qa import rag_answer_from_chunks


def rag_answer(
    *,
    question: str,
    chunks: list,
):
    """
    HIGH-LEVEL RAG ANSWER.
    Receives already-retrieved chunks.
    Returns MARKDOWN.
    """

    answer_md = rag_answer_from_chunks(
        question=question,
        chunks=chunks,
    )

    return answer_md