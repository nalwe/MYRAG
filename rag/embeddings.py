import numpy as np
import os
from openai import OpenAI


def get_openai_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is not set in environment variables")
    return OpenAI(api_key=api_key)


def embed_texts(texts):
    if not texts:
        return np.array([])

    client = get_openai_client()  # 🔥 Lazy initialization (safe for production)

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )

    return np.array([d.embedding for d in response.data])