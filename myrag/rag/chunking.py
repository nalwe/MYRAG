def chunk_text(text, size=500, overlap=100):
    words = text.split()
    chunks = []

    for i in range(0, len(words), size - overlap):
        chunk = " ".join(words[i:i + size])
        if chunk.strip():
            chunks.append(chunk)

    return chunks
