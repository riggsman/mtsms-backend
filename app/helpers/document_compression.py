"""Compress student-uploaded documents to fit size limits."""

from __future__ import annotations

import io
from pathlib import Path


def compress_image_to_limit(content: bytes, filename: str, max_bytes: int) -> tuple[bytes, str, str]:
    """Compress an image to fit within max_bytes. Returns (content, mime, filename)."""
    from PIL import Image

    image = Image.open(io.BytesIO(content))
    if image.mode in ("RGBA", "P"):
        image = image.convert("RGB")

    quality = 90
    width, height = image.size
    while quality >= 35:
        buf = io.BytesIO()
        image.save(buf, format="JPEG", optimize=True, quality=quality)
        candidate = buf.getvalue()
        if len(candidate) <= max_bytes:
            base = Path(filename).stem or "document"
            return candidate, "image/jpeg", f"{base}.jpg"
        quality -= 10
        if quality == 50:
            width = max(200, int(width * 0.85))
            height = max(200, int(height * 0.85))
            image = image.resize((width, height))

    raise ValueError("Could not compress image to size limit")


def compress_pdf_to_limit(content: bytes, filename: str, max_bytes: int) -> tuple[bytes, str, str]:
    """Compress a PDF to fit within max_bytes. Returns (content, mime, filename)."""
    import fitz

    if not content.startswith(b"%PDF"):
        raise ValueError("Invalid PDF content")

    source = fitz.open(stream=content, filetype="pdf")
    try:
        rewritten = source.write(garbage=4, deflate=True, clean=True)
        if len(rewritten) <= max_bytes:
            base = Path(filename).stem or "document"
            return rewritten, "application/pdf", f"{base}.pdf"

        scales = (1.0, 0.85, 0.7, 0.55, 0.45, 0.35)
        qualities = (85, 70, 55, 40, 30)

        for scale in scales:
            for quality in qualities:
                candidate_doc = fitz.open()
                try:
                    for page in source:
                        matrix = fitz.Matrix(scale, scale)
                        pixmap = page.get_pixmap(matrix=matrix, alpha=False)
                        jpeg_bytes = pixmap.tobytes("jpeg", jpg_quality=quality)
                        new_page = candidate_doc.new_page(width=pixmap.width, height=pixmap.height)
                        new_page.insert_image(new_page.rect, stream=jpeg_bytes)

                    candidate = candidate_doc.write(garbage=4, deflate=True, clean=True)
                    if len(candidate) <= max_bytes:
                        base = Path(filename).stem or "document"
                        return candidate, "application/pdf", f"{base}.pdf"
                finally:
                    candidate_doc.close()
    finally:
        source.close()

    raise ValueError("Could not compress PDF to size limit")
