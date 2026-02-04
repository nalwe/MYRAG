import os
from pdfminer.high_level import extract_text
import docx
from bs4 import BeautifulSoup


def extract_text_from_file(filepath):
    """
    Extract clean, readable text from supported file types
    for reliable RAG indexing.
    """

    if not filepath or not os.path.exists(filepath):
        return ""

    ext = os.path.splitext(filepath)[1].lower()

    # =========================
    # PDF
    # =========================
    if ext == ".pdf":
        try:
            text = extract_text(filepath)
            return _clean_text(text)
        except Exception:
            return ""

    # =========================
    # DOCX
    # =========================
    elif ext == ".docx":
        try:
            doc = docx.Document(filepath)
            text = "\n".join(
                p.text.strip() for p in doc.paragraphs if p.text.strip()
            )
            return _clean_text(text)
        except Exception:
            return ""

    # =========================
    # HTML
    # =========================
    elif ext == ".html":
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                soup = BeautifulSoup(f, "lxml")

            # Remove non-content elements
            for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
                tag.decompose()

            # Extract visible text
            text = soup.get_text(separator="\n")

            return _clean_text(text)
        except Exception:
            return ""

    # =========================
    # TXT
    # =========================
    elif ext == ".txt":
        try:
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return _clean_text(f.read())
        except Exception:
            return ""

    return ""


# =========================
# TEXT CLEANER (IMPORTANT)
# =========================

def _clean_text(text):
    """
    Normalize whitespace and remove empty lines.
    This dramatically improves embedding quality.
    """
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines()]
    lines = [line for line in lines if line]

    return "\n".join(lines)
