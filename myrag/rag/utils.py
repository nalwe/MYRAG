from django.db import models
from django.contrib.postgres.search import SearchQuery, SearchRank

from documents.models import Document
from accounts.services.quota import consume_tokens, QuotaExceeded
from accounts.services.token_estimator import estimate_tokens

from .models import ChatSession, ChatMessage
from .prompts import REPORT_TEMPLATE, STYLE_PRESETS


# =====================================================
# 🧠 ONBOARDING CHAT
# =====================================================

def create_onboarding_chat(user):
    """
    Create a welcome chat session for first-time users.
    """

    if ChatSession.objects.filter(user=user).exists():
        return

    session = ChatSession.objects.create(
        user=user,
        title="Welcome"
    )

    role = getattr(user.profile, "role", None)

    if role == "superuser":
        welcome = (
            "Welcome 👋\n\n"
            "As a **Platform Admin**, you can:\n"
            "• Upload global documents\n"
            "• Make documents public for ALL organizations\n"
            "• Manage organizations and users\n"
            "• Chat with all documents\n\n"
            "Start by uploading or asking a question."
        )

    elif role == "org_admin":
        welcome = (
            "Welcome 👋\n\n"
            "As an **Organization Admin**, you can:\n"
            "• Upload organization documents\n"
            "• Control document visibility inside your organization\n"
            "• Invite users\n"
            "• Chat with all company documents\n\n"
            "Start by uploading or asking a question."
        )

    elif role == "premium":
        welcome = (
            "Welcome 👋\n\n"
            "As a **Premium user**, you can:\n"
            "• Upload your own documents\n"
            "• Chat with company and public documents\n\n"
            "Upload a document or ask a question."
        )

    else:
        welcome = (
            "Welcome 👋\n\n"
            "You can chat with:\n"
            "• Public company documents\n"
            "• Global public documents\n\n"
            "Ask a question to get started."
        )

    ChatMessage.objects.create(
        session=session,
        role="assistant",
        content=welcome
    )


# =====================================================
# 🔐 API QUOTA ENFORCEMENT
# =====================================================

def enforce_quota(*, user, text: str):
    """
    Estimate tokens and deduct from organization quota.
    Superuser/global usage is ignored automatically.
    """
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
            "⚠️ Your organization has exceeded its API quota. "
            "Please contact your administrator."
        )


# =====================================================
# 🔎 DOCUMENT RETRIEVAL (PostgreSQL FTS)
# =====================================================

def retrieve_documents_for_chat(
    *,
    user,
    question,
    scope="all",
    folder_id=None,
    limit=3,
):
    """
    Retrieve relevant documents using PostgreSQL full-text search.
    Enforces organization isolation and global public visibility.
    """

    if not question:
        return Document.objects.none()

    profile = user.profile
    organization = profile.organization

    search_query = SearchQuery(question, search_type="websearch")

    # =========================
    # 🌍 VISIBILITY RULES
    # =========================
    visibility_filter = (
        # 🌍 Global public documents (superuser uploads)
        models.Q(
            organization__isnull=True,
            uploaded_by__isnull=True,
            is_public=True,
        )
        |
        # 🏢 Organization documents
        models.Q(
            organization=organization
        )
        |
        # 👤 Personal documents
        models.Q(
            uploaded_by=user
        )
    )

    qs = (
        Document.objects
        .annotate(rank=SearchRank("search_vector", search_query))
        .filter(rank__gt=0)
        .filter(visibility_filter)
    )

    if scope == "folder" and folder_id:
        qs = qs.filter(folder_id=folder_id)

    return qs.order_by("-rank")[:limit]


# =====================================================
# ⚖️ LEGAL DOCUMENT DETECTION (STRICT)
# =====================================================

def is_legal_document(title: str, text: str) -> bool:
    """
    Identify real statutes ONLY (title-based).
    """
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


# =====================================================
# ⚖️ LEGAL QUESTION MODE DETECTION
# =====================================================

def detect_legal_question_mode(question: str) -> str:
    """
    Detect whether legal question requires ENUMERATION or ANALYSIS.
    """
    q = (question or "").lower()

    enumeration_triggers = [
        "sections of",
        "list the sections",
        "arrangement of sections",
        "parts of the act",
        "list the parts",
        "structure of the act",
        "what are the sections",
        "what are the parts",
    ]

    for trigger in enumeration_triggers:
        if trigger in q:
            return "enumeration"

    return "analysis"


# =====================================================
# 🤖 CHAT WITH CONTEXT (STRICT LEGAL BEHAVIOUR)
# =====================================================

def chat_with_context(
    *,
    user,
    retrieved_chunks,
    question: str,
    legal_mode: str | None,
    style="executive",
    prepared_by="System Generated",
):
    """
    Question-aware, statute-safe answering.
    Enumeration FAILS if structure is not visible.
    """

    style_config = STYLE_PRESETS.get(style, STYLE_PRESETS["executive"])

    # =========================
    # TOKEN LIMITS
    # =========================
    MAX_CHUNKS = 5
    MAX_CHARS_PER_CHUNK = 2000
    MAX_SOURCE_CHARS = 8000

    # =========================
    # PREPARE SOURCE MATERIAL
    # =========================
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

    # =========================
    # 🔐 ENFORCE API QUOTA
    # =========================
    enforce_quota(
        user=user,
        text=question + source_material
    )

    # =========================
    # ROUTING
    # =========================
    is_legal = is_legal_document(document_title, source_material)

    # =========================
    # ⚖️ LEGAL — ENUMERATION
    # =========================
    if is_legal and legal_mode == "enumeration":
        system_prompt = (
            "You are a LEGAL EXTRACTION ENGINE.\n"
            "You ONLY extract statutory structure if it is explicitly present.\n"
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

    # =========================
    # ⚖️ LEGAL — ANALYSIS
    # =========================
    elif is_legal:
        system_prompt = (
            "You are a LEGAL ANALYSIS ASSISTANT.\n"
            "You analyse statutes using statutory language only.\n"
            "You NEVER use report or meeting formats."
        )

        user_prompt = f"""
REFERENCE MATERIAL:
{source_material}

TASK:
Analyse this law.

OUTPUT STRUCTURE:
- Purpose and Scope
- Powers and Authorities
- Duties and Obligations
- Procedures
- Prohibitions
- Enforcement and Penalties (if any)
"""

    # =========================
    # 📄 NON-LEGAL REPORT
    # =========================
    else:
        system_prompt = "You are a PROFESSIONAL REPORTING ASSISTANT."

        user_prompt = f"""
REFERENCE POINTS:
{source_material}

TASK:
Create a professional report.

STYLE:
- Tone: {style_config['tone']}
- Depth: {style_config['depth']}
- Focus: {style_config['focus']}

MANDATORY TEMPLATE:
{REPORT_TEMPLATE}

Prepared By:
{prepared_by}
"""

    # =========================
    # OPENAI CALL
    # =========================
    from openai import OpenAI
    client = OpenAI()

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.2,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
    )

    return response.choices[0].message.content.strip()
