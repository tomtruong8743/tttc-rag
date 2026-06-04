"""
Ingest documents from data/documents/ into ChromaDB.

Supported formats: PDF, DOCX, TXT, Markdown (.md)
Each chunk is stored with metadata: source, page (if available), chunk_index.
"""

import os
import re
import sys
from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

DATA_DIR = Path("data/documents")
CHROMA_DIR = Path("chroma_db")
COLLECTION_NAME = "documents"
CHUNK_SIZE = 1500      # characters — larger chunks preserve more context per decree article
CHUNK_OVERLAP = 200    # characters

# Must match retrieval.py
EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"


TESSERACT_PATH = "/opt/homebrew/bin/tesseract"
TESSDATA_PATH  = "/opt/homebrew/share/tessdata"

def extract_text_pdf(path: Path) -> list[dict]:
    """Extract text from every page of a PDF.

    Strategy:
    1. Try PyMuPDF direct text extraction (fast, works for digital PDFs)
    2. If a page returns no text, fall back to OCR via pytesseract
       (handles scanned/image-only pages — common in Vietnamese govt docs)
    """
    import fitz
    doc = fitz.open(str(path))
    pages = []

    # Check if OCR is available
    ocr_available = False
    try:
        import pytesseract
        from PIL import Image
        import io
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
        ocr_available = True
    except ImportError:
        print(f"  [warn] pytesseract not installed — scanned pages will be skipped.")

    for i, page in enumerate(doc, start=1):
        text = page.get_text().strip()

        if not text and ocr_available:
            # Render page as image and OCR it
            try:
                mat = fitz.Matrix(2.0, 2.0)  # 2x scale for better OCR accuracy
                pix = page.get_pixmap(matrix=mat)
                img = Image.open(io.BytesIO(pix.tobytes("png")))
                # Try Vietnamese first, fall back to English
                lang = "vie+eng" if _tesseract_has_vie() else "eng"
                text = pytesseract.image_to_string(img, lang=lang, config="--psm 1")
                text = text.strip()
                if text:
                    print(f"  [ocr] page {i} of {path.name}")
            except Exception as e:
                print(f"  [ocr error] page {i}: {e}")
                text = ""

        if text:
            pages.append({"text": text, "page": i})

    doc.close()
    return pages


def _tesseract_has_vie() -> bool:
    """Check if Vietnamese language data is available for tesseract."""
    import subprocess
    try:
        result = subprocess.run(
            [TESSERACT_PATH, "--list-langs"],
            capture_output=True, text=True
        )
        return "vie" in result.stdout + result.stderr
    except Exception:
        return False


def extract_text_docx(path: Path) -> list[dict]:
    """DOCX has no pages; return single chunk with page=None."""
    from docx import Document
    doc = Document(str(path))
    text = "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return [{"text": text, "page": None}]


def extract_text_plain(path: Path) -> list[dict]:
    text = path.read_text(encoding="utf-8", errors="replace")
    return [{"text": text, "page": None}]


def extract_text(path: Path) -> list[dict]:
    suffix = path.suffix.lower()
    if suffix == ".pdf":
        return extract_text_pdf(path)
    if suffix == ".docx":
        return extract_text_docx(path)
    if suffix in (".txt", ".md"):
        return extract_text_plain(path)
    return []


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> list[str]:
    """Split text into overlapping character-level chunks."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + size
        chunks.append(text[start:end])
        start += size - overlap
    return chunks


def ingest():
    if not DATA_DIR.exists():
        print(f"[error] {DATA_DIR} does not exist.")
        sys.exit(1)

    files = [f for f in DATA_DIR.iterdir() if f.is_file()]
    if not files:
        print(f"[warn] No files found in {DATA_DIR}.")
        return

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
    collection = client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)

    total_chunks = 0
    for file_path in files:
        pages = extract_text(file_path)
        if not pages:
            print(f"[skip] Unsupported or empty: {file_path.name}")
            continue

        print(f"[ingest] {file_path.name} ({len(pages)} page/section(s))")
        chunk_index = 0
        for page_data in pages:
            for chunk in chunk_text(page_data["text"]):
                if not chunk.strip():
                    continue
                doc_id = f"{file_path.name}__p{page_data['page']}__c{chunk_index}"
                metadata = {
                    "source": file_path.name,
                    "page": str(page_data["page"]) if page_data["page"] else "N/A",
                    "chunk_index": chunk_index,
                }
                collection.upsert(
                    ids=[doc_id],
                    documents=[chunk],
                    metadatas=[metadata],
                )
                chunk_index += 1
                total_chunks += 1

    print(f"\n[done] Ingested {total_chunks} chunks from {len(files)} file(s).")


if __name__ == "__main__":
    ingest()
