import os
from pdfminer.high_level import extract_text as pdf_extract_text
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import docx


def extract_text_from_file(filepath):
    """
    Extract text from supported file types.
    Expects a REAL file path (e.g., doc.file.path).
    """

    if not filepath or not os.path.exists(filepath):
        return ""

    ext = os.path.splitext(filepath)[1].lower()

    # =========================
    # 📄 PDF (Text-Based First)
    # =========================
    if ext == ".pdf":
        try:
            text = pdf_extract_text(filepath)
            if text and text.strip():
                return text.strip()
        except Exception as e:
            print(f"[PDF TEXT EXTRACTION FAILED] {e}")

        # 🔁 Fallback to OCR (for scanned PDFs)
        try:
            images = convert_from_path(filepath)
            ocr_text = "\n".join(
                pytesseract.image_to_string(img) for img in images
            )
            return ocr_text.strip()
        except Exception as e:
            print(f"[PDF OCR FAILED] {e}")
            return ""

    # =========================
    # 📄 DOCX (Word Documents)
    # =========================
    if ext == ".docx":
        try:
            d = docx.Document(filepath)
            text = "\n".join(p.text for p in d.paragraphs)
            return text.strip()
        except Exception as e:
            print(f"[DOCX EXTRACTION FAILED] {e}")
            return ""

    # =========================
    # 🖼 Images (OCR)
    # =========================
    if ext in [".png", ".jpg", ".jpeg"]:
        try:
            return pytesseract.image_to_string(Image.open(filepath)).strip()
        except Exception as e:
            print(f"[IMAGE OCR FAILED] {e}")
            return ""

    return ""