import numpy as np
from .faiss_utils import load_or_create_index, save_index
from .chunking import chunk_text
from .embeddings import embed_texts

def index_document(doc):
    if doc.is_public and doc.uploaded_by_admin:
        index_name = "public"
    else:
        index_name = f"private_{doc.owner.id}"

    index, chunks = load_or_create_index(index_name)

    text_chunks = chunk_text(doc.extracted_text)
    if not text_chunks:
        return

    embeddings = embed_texts(text_chunks)

    index.add(np.array(embeddings))

    for text in text_chunks:
        chunks.append({
            "text": text,
            "doc_id": doc.id,
            "doc_name": doc.file.name.split("/")[-1],
        })

    save_index(index_name, index, chunks)
