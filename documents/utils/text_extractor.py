import os
from pdfminer.high_level import extract_text
from pdf2image import convert_from_path
import pytesseract
from PIL import Image
import docx


def extract_text_from_file(filepath):
    if not filepath or not os.path.exists(filepath):
        return ""

    ext = os.path.splitext(filepath)[1].lower()

    # ✅ PDF (text-based)
    if ext == ".pdf":
        text = extract_text(filepath)
        if text and text.strip():
            return text

        # 🔁 fallback to OCR (scanned PDF)
        images = convert_from_path(filepath)
        return "\n".join(
            pytesseract.image_to_string(img) for img in images
        )

    # ✅ Word
    if ext == ".docx":
        d = docx.Document(filepath)
        return "\n".join(p.text for p in d.paragraphs)

    # ✅ Images
    if ext in [".png", ".jpg", ".jpeg"]:
        return pytesseract.image_to_string(Image.open(filepath))

    return ""
