import numpy as np
from django.conf import settings


# =====================================================
# 🔐 OPENAI CLIENT (LAZY, RUNTIME ONLY)
# =====================================================

def require_openai():
    """
    Lazily create OpenAI client.
    NEVER runs during import / collectstatic.
    """
    if not settings.OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY is required to generate embeddings")

    from openai import OpenAI
    return OpenAI(api_key=settings.OPENAI_API_KEY)


# =====================================================
# 🧠 EMBEDDINGS
# =====================================================

def embed_texts(texts):
    """
    Generate embeddings for a list of texts.
    """
    if not texts:
        return np.array([])

    client = require_openai()

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )

    return np.array([item.embedding for item in response.data])
