"""
FastAPI server for the VIFC Knowledge Assistant website.

Routes:
  GET  /              — chat UI
  POST /ask           — RAG question answering
  GET  /upload        — document upload page
  POST /upload        — submit a document for review
  GET  /admin         — admin login page
  POST /admin/login   — verify admin password
  GET  /admin/review  — review pending documents (protected)
  POST /admin/approve — approve a document and ingest it
  POST /admin/reject  — reject a document

Usage:
    cd /Users/tommyt/Desktop/INFO
    ADMIN_PASSWORD=yourpassword python3 website/server.py
"""

import hashlib
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

import uvicorn
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from starlette.middleware.sessions import SessionMiddleware

from answer import generate_answer
from ingest import extract_text, chunk_text, EMBEDDING_MODEL, COLLECTION_NAME, CHROMA_DIR
from retrieval import format_citation

BASE_DIR   = Path(__file__).parent
ROOT_DIR   = BASE_DIR.parent
PENDING    = ROOT_DIR / "data" / "pending"
REJECTED   = ROOT_DIR / "data" / "rejected"
APPROVED   = ROOT_DIR / "data" / "documents"
META_FILE  = PENDING / "_meta.json"   # tracks submitter info per file

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".txt", ".md"}
MAX_FILE_SIZE_MB   = 20
ADMIN_PASSWORD     = os.environ.get("ADMIN_PASSWORD", "vifc-admin-2026")

app = FastAPI(title="VIFC Knowledge Assistant")
app.add_middleware(SessionMiddleware, secret_key=os.environ.get("SECRET_KEY", "vifc-secret-key-change-me"))
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

PENDING.mkdir(parents=True, exist_ok=True)
REJECTED.mkdir(parents=True, exist_ok=True)


# ── Helpers ───────────────────────────────────────────────────────

def load_meta() -> dict:
    if META_FILE.exists():
        return json.loads(META_FILE.read_text())
    return {}

def save_meta(meta: dict):
    META_FILE.write_text(json.dumps(meta, indent=2))

def is_admin(request: Request) -> bool:
    return request.session.get("is_admin") is True

def hash_password(pw: str) -> str:
    return hashlib.sha256(pw.encode()).hexdigest()


# ── Chat ──────────────────────────────────────────────────────────

class Question(BaseModel):
    question: str
    top_k: int = 15

@app.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/ask")
async def ask(body: Question):
    if not body.question.strip():
        return JSONResponse({"error": "Please enter a question."}, status_code=400)
    try:
        result = generate_answer(body.question.strip(), top_k=body.top_k)

        # Build sources list from chunks or wiki page
        if result.get("chunks"):
            sources = list(dict.fromkeys(format_citation(c) for c in result["chunks"]))
        elif result.get("wiki_path"):
            sources = [result.get("source_label", str(result["wiki_path"].name))]
        else:
            sources = []

        return {
            "answer": result["answer"],
            "sources": sources,
            "wiki_created": result.get("wiki_created", False),
            "wiki_name": result["wiki_path"].stem.replace("_", " ").title() if result.get("wiki_path") else None,
        }
    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Upload ────────────────────────────────────────────────────────

@app.get("/upload")
async def upload_page(request: Request):
    return templates.TemplateResponse("upload.html", {"request": request})

@app.post("/upload")
async def upload_document(
    request: Request,
    file: UploadFile = File(...),
    submitter_name: str = Form(""),
    submitter_email: str = Form(""),
    description: str = Form(""),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        return JSONResponse({"error": f"File type '{suffix}' is not supported. Allowed: PDF, DOCX, TXT, MD."}, status_code=400)

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE_MB * 1024 * 1024:
        return JSONResponse({"error": f"File exceeds {MAX_FILE_SIZE_MB}MB limit."}, status_code=400)

    # Save with timestamp prefix to avoid name collisions
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    safe_name = re.sub(r"[^\w\-.]", "_", file.filename)
    save_name = f"{timestamp}__{safe_name}"
    dest = PENDING / save_name
    dest.write_bytes(contents)

    # Save metadata
    meta = load_meta()
    meta[save_name] = {
        "original_name": file.filename,
        "submitter_name": submitter_name,
        "submitter_email": submitter_email,
        "description": description,
        "submitted_at": datetime.now().isoformat(),
        "size_kb": round(len(contents) / 1024, 1),
    }
    save_meta(meta)

    return templates.TemplateResponse("upload.html", {
        "request": request,
        "success": f"'{file.filename}' submitted successfully. It will be reviewed before being added to the database."
    })


# ── Admin Login ───────────────────────────────────────────────────

class PasswordCheck(BaseModel):
    password: str

@app.post("/admin/verify")
async def admin_verify(request: Request, body: PasswordCheck):
    """Called by the floating FAB to verify the password via JSON."""
    if body.password == ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return {"ok": True}
    return {"ok": False}


@app.get("/admin")
async def admin_login_page(request: Request):
    if is_admin(request):
        return RedirectResponse("/admin/review")
    return templates.TemplateResponse("admin_login.html", {"request": request})

@app.post("/admin/login")
async def admin_login(request: Request, password: str = Form(...)):
    if password == ADMIN_PASSWORD:
        request.session["is_admin"] = True
        return RedirectResponse("/admin/review", status_code=303)
    return templates.TemplateResponse("admin_login.html", {
        "request": request,
        "error": "Incorrect password."
    })

@app.get("/admin/logout")
async def admin_logout(request: Request):
    request.session.clear()
    return RedirectResponse("/admin")


# ── Admin Review ──────────────────────────────────────────────────

@app.get("/admin/review")
async def admin_review(request: Request):
    if not is_admin(request):
        return RedirectResponse("/admin")

    meta = load_meta()
    pending_files = []
    for f in sorted(PENDING.iterdir()):
        if f.name.startswith("_") or not f.is_file():
            continue
        info = meta.get(f.name, {})
        pending_files.append({
            "filename": f.name,
            "original_name": info.get("original_name", f.name),
            "submitter_name": info.get("submitter_name", "Unknown"),
            "submitter_email": info.get("submitter_email", ""),
            "description": info.get("description", ""),
            "submitted_at": info.get("submitted_at", ""),
            "size_kb": info.get("size_kb", "?"),
        })

    return templates.TemplateResponse("admin_review.html", {
        "request": request,
        "pending_files": pending_files,
    })

@app.post("/admin/approve")
async def admin_approve(request: Request, filename: str = Form(...)):
    if not is_admin(request):
        raise HTTPException(status_code=403)

    src = PENDING / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    # Move to documents folder
    meta = load_meta()
    original_name = meta.get(filename, {}).get("original_name", filename)
    dest = APPROVED / original_name
    # Avoid overwriting existing files
    if dest.exists():
        stem = dest.stem
        dest = APPROVED / f"{stem}__{filename[:15]}{dest.suffix}"
    shutil.move(str(src), str(dest))

    # Ingest into ChromaDB
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name=EMBEDDING_MODEL)
        collection = client.get_or_create_collection(COLLECTION_NAME, embedding_function=ef)

        pages = extract_text(dest)
        chunk_index = 0
        for page_data in pages:
            for chunk in chunk_text(page_data["text"]):
                if not chunk.strip():
                    continue
                doc_id = f"{dest.name}__p{page_data['page']}__c{chunk_index}"
                collection.upsert(
                    ids=[doc_id],
                    documents=[chunk],
                    metadatas={
                        "source": dest.name,
                        "page": str(page_data["page"]) if page_data["page"] else "N/A",
                        "chunk_index": chunk_index,
                    },
                )
                chunk_index += 1
        ingest_msg = f"Ingested {chunk_index} chunks."
    except Exception as e:
        ingest_msg = f"File approved but ingestion failed: {e}"

    # Remove from meta
    meta.pop(filename, None)
    save_meta(meta)

    return RedirectResponse(f"/admin/review?message=Approved+and+ingested:+{original_name}+({ingest_msg})", status_code=303)

@app.post("/admin/reject")
async def admin_reject(request: Request, filename: str = Form(...)):
    if not is_admin(request):
        raise HTTPException(status_code=403)

    src = PENDING / filename
    if not src.exists():
        raise HTTPException(status_code=404, detail="File not found.")

    shutil.move(str(src), str(REJECTED / filename))

    meta = load_meta()
    original_name = meta.get(filename, {}).get("original_name", filename)
    meta.pop(filename, None)
    save_meta(meta)

    return RedirectResponse(f"/admin/review?message=Rejected:+{original_name}", status_code=303)


if __name__ == "__main__":
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY is not set.")
        sys.exit(1)
    print(f"[info] Admin password: {ADMIN_PASSWORD}")
    print(f"[info] Set ADMIN_PASSWORD env var to change it.")
    uvicorn.run("server:app", host="0.0.0.0", port=8000, reload=True,
                app_dir=str(BASE_DIR))
