
from openai import OpenAI

client = OpenAI()





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
        f"[S{i+1}]\n{c['text']}"
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
    # Ensure every answer starts with a heading
    if not answer.startswith("##"):
        answer = "## Answer\n\n" + answer

    return answer
