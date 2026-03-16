"""
Pure PDF processing functions.

These functions take raw bytes and return structured data. They can be called
from an HTTP handler, a CloudEvents handler, a CLI, or any other entrypoint.
"""

import io
import zipfile
from typing import Any

from pypdf import PdfReader, PdfWriter

MAX_ZIP_TOTAL = 10 * 1024 * 1024  # 10 MB decompressed

PDF_MAGIC = b"%PDF"


class InvalidPDFError(Exception):
    """Raised when input bytes are not a valid PDF."""


class ProcessingError(Exception):
    """Raised when a valid PDF cannot be processed (e.g., corrupt structure)."""


def validate_pdf_header(data: bytes) -> None:
    """Check that *data* starts with the PDF magic bytes."""
    if not data or not data[:4].startswith(PDF_MAGIC):
        raise InvalidPDFError("Input is not a PDF file (missing %PDF header)")

def extract_text(pdf_bytes: bytes) -> str:
    """Extract all text content from a PDF.

    Returns the concatenated text of every page separated by newlines.
    """
    validate_pdf_header(pdf_bytes)
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        return "\n".join(page.extract_text() or "" for page in reader.pages)
    except InvalidPDFError:
        raise
    except Exception:
        raise ProcessingError("Failed to extract text from PDF")


def get_metadata(pdf_bytes: bytes) -> dict[str, Any]:
    """Return metadata for a PDF.

    Includes page info, document properties, and page dimensions.
    """
    validate_pdf_header(pdf_bytes)
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        m = reader.metadata

        # Page dimensions from first page (PDF unit is 1 point = 1/72 inch, per ISO 32000)
        page_size = None
        if reader.pages:
            media = reader.pages[0].mediabox
            w = media[2] - media[0]  # upper-right x - lower-left x
            h = media[3] - media[1]  # upper-right y - lower-left y
            page_size = {
                "width_pt": w,
                "height_pt": h,
                "width_cm": round(w / 72 * 2.54, 2),
                "height_cm": round(h / 72 * 2.54, 2),
            }

        # Total text length as a rough content indicator
        total_chars = sum(len(page.extract_text() or "") for page in reader.pages)

        return {
            "pages": len(reader.pages),
            "title": m.title if m else None,
            "author": m.author if m else None,
            "creator": m.creator if m else None,
            "producer": m.producer if m else None,
            "subject": m.subject if m else None,
            "creation_date": str(m.creation_date) if m and m.creation_date else None,
            "modification_date": str(m.modification_date) if m and m.modification_date else None,
            "page_size": page_size,
            "total_characters": total_chars,
            "encrypted": reader.is_encrypted,
        }
    except InvalidPDFError:
        raise
    except Exception:
        raise ProcessingError("Failed to read PDF metadata")


def split_pages(pdf_bytes: bytes) -> bytes:
    """Split a PDF into individual pages returned as a ZIP archive.

    Each page is stored as ``page_1.pdf``, ``page_2.pdf``, etc.
    """
    validate_pdf_header(pdf_bytes)
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
        if len(reader.pages) == 0:
            raise InvalidPDFError("PDF has no pages")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            for i, page in enumerate(reader.pages):
                w = PdfWriter()
                w.add_page(page)
                pbuf = io.BytesIO()
                w.write(pbuf)
                zf.writestr(f"page_{i + 1}.pdf", pbuf.getvalue())
        return buf.getvalue()
    except InvalidPDFError:
        raise
    except Exception:
        raise ProcessingError("Failed to split PDF pages")


def merge_pdfs(zip_bytes: bytes) -> bytes:
    """Merge multiple PDFs packed in a ZIP archive into a single PDF.

    The ZIP is scanned for ``.pdf`` files (sorted by name). A decompression
    bomb guard limits total uncompressed size to MAX_ZIP_TOTAL.
    """
    try:
        zf_stream = io.BytesIO(zip_bytes)
        if not zipfile.is_zipfile(zf_stream):
            raise InvalidPDFError("Input is not a valid ZIP file")
        zf_stream.seek(0)

        writer = PdfWriter()
        with zipfile.ZipFile(zf_stream) as zf:
            total = sum(info.file_size for info in zf.infolist())
            if total > MAX_ZIP_TOTAL:
                raise InvalidPDFError("ZIP content exceeds 10 MB decompression limit")

            pdfs = sorted(n for n in zf.namelist() if n.endswith(".pdf"))
            if not pdfs:
                raise InvalidPDFError("ZIP contains no .pdf files")

            for name in pdfs:
                pdf_data = zf.read(name)
                for page in PdfReader(io.BytesIO(pdf_data)).pages:
                    writer.add_page(page)

        buf = io.BytesIO()
        writer.write(buf)
        return buf.getvalue()
    except InvalidPDFError:
        raise
    except Exception:
        raise ProcessingError("Failed to merge PDFs")
