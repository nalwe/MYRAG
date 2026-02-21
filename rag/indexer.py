import numpy as np
from .faiss_utils import load_or_create_index, save_index
from .chunking import chunk_text
from .embeddings import embed_texts


def index_document(doc):
    # ✅ Correct index selection logic
    if doc.is_public:
        index_name = "public"
    else:
        index_name = f"user_{doc.uploaded_by.id}"

    index, chunks = load_or_create_index(index_name)

    # Split into chunks
    text_chunks = chunk_text(doc.extracted_text)
    if not text_chunks:
        print("[INDEXING STOPPED] No chunks generated.")
        return

    # Generate embeddings
    embeddings = embed_texts(text_chunks)

    if len(embeddings) == 0:
        print("[INDEXING STOPPED] No embeddings returned.")
        return

    # Add vectors to FAISS
    index.add(np.array(embeddings))

    # Store metadata
    for text in text_chunks:
        chunks.append({
            "text": text,
            "doc_id": doc.id,
            "doc_name": doc.file.name.split("/")[-1],
        })

    save_index(index_name, index, chunks)

    print(f"[INDEX SUCCESS] {len(text_chunks)} chunks indexed into '{index_name}'")