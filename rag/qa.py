import os
from openai import OpenAI


def get_openai_client() -> OpenAI:
    """
    Lazily initialize OpenAI client.
    Prevents Django from crashing at import time.
    """
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    return OpenAI(api_key=api_key)


def rag_answer_from_chunks(
    *,
    question: str,
    chunks: list[dict],
) -> str:
    """
    LOW-LEVEL RAG EXECUTOR.
    Uses ONLY provided chunks.
    Returns CLEAN, STRUCTURED MARKDOWN.
    """

    if not chunks:
        return (
            "## Answer\n\n"
            "The document does not contain enough information "
            "to answer this question."
        )

    # =========================
    # PREPARE SOURCES
    # =========================
    sources_text = "\n\n".join(
        f"[S{i + 1}]\n{c['text']}"
        for i, c in enumerate(chunks)
    )

    # =========================
    # SYSTEM PROMPT (STRICT + CLEAN OUTPUT)
    # =========================
    system_prompt = (
        "You are a retrieval-augmented assistant.\n"
        "You MUST answer using ONLY the sources provided.\n"
        "You MUST NOT use external knowledge.\n"
        "If the answer is not explicitly present, say so clearly.\n\n"
        "MANDATORY FORMAT RULES:\n"
        "- Output MUST be valid Markdown\n"
        "- Start with a clear heading (##)\n"
        "- Use bullet points for lists\n"
        "- Use short, precise lines\n"
        "- Leave a blank line between sections\n"
        "- Do NOT write long paragraphs\n"
        "- Do NOT repeat the sources verbatim\n"
    )

    # =========================
    # USER PROMPT
    # =========================
    user_prompt = f"""
SOURCES:
{sources_text}

QUESTION:
{question}

INSTRUCTIONS:
- Structure the answer clearly
- Prefer lists over prose
- If listing items (e.g. sections), list them cleanly
"""

    # =========================
    # OPENAI CALL (LAZY INIT)
    # =========================
    client = get_openai_client()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    answer = response.choices[0].message.content.strip()

    # =========================
    # FINAL SANITY CLEANUP
    # =========================
    if not answer.startswith("##"):
        answer = "## Answer\n\n" + answer

    return answer
