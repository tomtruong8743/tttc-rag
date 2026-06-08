#!/usr/bin/env python3
"""
Direct bulk ingest to ChromaDB — no admin review, instant indexing.

Usage:
    python3 bulk_ingest_direct.py https://your-railway-url.app

This script:
1. Reads all files from data/documents/
2. Uploads them to /ingest-direct endpoint
3. Files are indexed immediately (no admin review)
"""

import sys
import os
from pathlib import Path
import requests
from urllib.parse import urljoin

# Config
DATA_DIR = Path(__file__).parent / "data" / "documents"
ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md"}

def bulk_ingest_direct(base_url: str):
    """Ingest all documents directly into ChromaDB."""

    if not DATA_DIR.exists():
        print(f"❌ No documents folder found: {DATA_DIR}")
        return

    docs = list(DATA_DIR.glob("*"))
    docs = [d for d in docs if d.is_file() and d.suffix.lower() in ALLOWED_EXTS]

    if not docs:
        print(f"❌ No documents found in {DATA_DIR}")
        return

    print(f"🚀 Direct ingesting {len(docs)} documents\n")

    ingested = []
    failed = []
    total_chunks = 0

    for i, doc_path in enumerate(docs, 1):
        print(f"[{i}/{len(docs)}] {doc_path.name}...", end=" ")

        try:
            with open(doc_path, "rb") as f:
                files = {"file": (doc_path.name, f)}
                ingest_url = urljoin(base_url, "/ingest-direct")
                resp = requests.post(ingest_url, files=files, timeout=120)
                resp.raise_for_status()

                result = resp.json()
                chunks = result.get("chunks_ingested", 0)
                total_chunks += chunks
                print(f"✅ ({chunks} chunks)")
                ingested.append(doc_path.name)

        except Exception as e:
            print(f"❌ {e}")
            failed.append((doc_path.name, str(e)))

    print(f"\n{'='*60}")
    print(f"✅ Ingested: {len(ingested)}/{len(docs)} ({total_chunks} total chunks)")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for name, err in failed:
            print(f"   - {name}: {err}")
    else:
        print("🎉 All documents ready to query immediately!")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 bulk_ingest_direct.py <railway-url>")
        print("\nExample:")
        print("  python3 bulk_ingest_direct.py https://tttc-rag-production.up.railway.app")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    bulk_ingest_direct(base_url)
