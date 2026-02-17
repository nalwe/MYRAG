import os
from openai import OpenAI

from accounts.services.quota import consume_tokens, QuotaExceeded
from accounts.services.token_estimator import estimate_tokens

from .prompts import (
    REPORT_TEMPLATE,
    STYLE_PRESETS,
    REPORTING_SYSTEM_PROMPT,
    LEGAL_SYSTEM_PROMPT,
)


# =========================
# 🔐 SAFE OPENAI CLIENT
# =========================

def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")

    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    return OpenAI(api_key=api_key)


# =========================
# LEGAL DOCUMENT DETECTOR
# =========================

def is_legal_document(title, text):
    if not title:
        return False

    title = title.lower()

    legal_title_markers = [
        " act",
        " bill",
        " statute",
        " constitution",
        " regulations",
        " ordinance",
        " code of law",
    ]

    return any(marker in title for marker in legal_title_markers)


# =========================
# 🔐 TOKEN ENFORCEMENT HELPER
# =========================

def enforce_quota(*, user, text: str):
    profile = user.profile
    organization = profile.organization

    estimated_tokens = estimate_tokens(text)

    try:
        consume_tokens(
            organization=organization,
            tokens=estimated_tokens,
        )
    except QuotaExceeded:
        raise QuotaExceeded(
            "Your organization has exceeded its API quota. "
            "Please contact your administrator."
        )


# =========================
# Q&A MODE
# =========================

def chat_with_docs(*, user, query, chunk_results):
    context = "\n\n".join(
        c["text"] for c in chunk_results
    ) if chunk_results else ""

    enforce_quota(user=user, text=query + context)

    client = get_openai_client()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {
                "role": "system",
                "content": (
                    "You are a document assistant. "
                    "Answer ONLY using the provided context. "
                    "If the answer is not in the context, say: "
                    "'I could not find this information in the documents.'"
                ),
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{query}",
            },
        ],
    )

    answer = response.choices[0].message.content.strip()

    if chunk_results:
        confidence = round(
            sum(1 / (1 + c.get("score", 0)) for c in chunk_results)
            / len(chunk_results),
            2,
        )
    else:
        confidence = 0.0

    sources = sorted({c["document_title"] for c in chunk_results})

    cited_chunks = [
        {
            "text": c["text"],
            "document_title": c["document_title"],
            "document_id": c["document_id"],
        }
        for c in chunk_results
    ]

    return answer, sources, cited_chunks, confidence


# =========================
# REPORT / LEGAL MODE
# =========================

def chat_with_context(
    *,
    user,
    retrieved_chunks,
    question: str,
    legal_mode: str | None,
    style="executive",
    prepared_by="System Generated"
):
    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["executive"])

    MAX_CHUNKS = 5
    MAX_CHARS_PER_CHUNK = 2000
    MAX_SOURCE_CHARS = 8000

    cleaned_chunks = []

    for chunk in retrieved_chunks[:MAX_CHUNKS]:
        text = (chunk.get("text") or "").strip()
        if not text:
            continue

        cleaned_chunks.append(text[:MAX_CHARS_PER_CHUNK])

    source_material = "\n\n".join(cleaned_chunks)[:MAX_SOURCE_CHARS]

    document_title = (
        retrieved_chunks[0].get("document_title", "")
        if retrieved_chunks
        else ""
    )

    enforce_quota(
        user=user,
        text=question + source_material
    )

    is_legal = is_legal_document(document_title, source_material)

    if is_legal and legal_mode == "enumeration":
        system_prompt = (
            "You are a LEGAL EXTRACTION ENGINE.\n"
            "You extract statutory structure ONLY when explicitly present.\n"
            "You NEVER summarise, infer, or restructure laws."
        )

        user_prompt = f"""
REFERENCE MATERIAL:
{source_material}

TASK:
List the SECTIONS of this Act.

STRICT RULES:
- ONLY list sections that are explicitly visible
- Do NOT summarise
- Do NOT group thematically
- Do NOT invent structure
- If sections are NOT visible, you MUST say so
"""

    elif is_legal:
        system_prompt = LEGAL_SYSTEM_PROMPT.strip()

        user_prompt = f"""
REFERENCE MATERIAL:
{source_material}

TASK:
Analyse this law as a statutory instrument.
"""

    else:
        system_prompt = REPORTING_SYSTEM_PROMPT.strip()

        user_prompt = f"""
REFERENCE POINTS:
{source_material}

TASK:
Create a professional, non-legal report.

STYLE:
- Tone: {style_config['tone']}
- Depth: {style_config['depth']}
- Focus: {style_config['focus']}

MANDATORY TEMPLATE:
{REPORT_TEMPLATE}

Prepared By:
{prepared_by}
"""

    client = get_openai_client()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content.strip()
