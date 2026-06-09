#!/usr/bin/env python3
"""
Bulk upload documents to Railway VIFC Knowledge Assistant.

Usage:
    python3 bulk_upload.py https://your-railway-url.app

This script:
1. Reads all documents from data/documents/
2. Uploads them to the remote server
3. Auto-approves them
"""

import sys
import os
from pathlib import Path
import requests
from urllib.parse import urljoin

# Config
DATA_DIR = Path(__file__).parent / "data" / "documents"
ALLOWED_EXTS = {".pdf", ".docx", ".txt", ".md"}

def bulk_upload(base_url: str, admin_password: str):
    """Upload all documents from data/documents/ to the server."""

    if not DATA_DIR.exists():
        print(f"❌ No documents folder found: {DATA_DIR}")
        return

    docs = list(DATA_DIR.glob("*"))
    docs = [d for d in docs if d.is_file() and d.suffix.lower() in ALLOWED_EXTS]

    if not docs:
        print(f"❌ No documents found in {DATA_DIR}")
        return

    print(f"📄 Found {len(docs)} documents to upload\n")

    uploaded = []
    failed = []

    for i, doc_path in enumerate(docs, 1):
        print(f"[{i}/{len(docs)}] Uploading {doc_path.name}...", end=" ")

        try:
            # Upload document
            with open(doc_path, "rb") as f:
                files = {"file": (doc_path.name, f)}
                data = {"submitter_email": "bulk-import@vifc.local"}

                upload_url = urljoin(base_url, "/upload")
                resp = requests.post(upload_url, files=files, data=data, timeout=60)
                resp.raise_for_status()

            print("✅ Uploaded")
            uploaded.append(doc_path.name)

        except Exception as e:
            print(f"❌ Failed: {e}")
            failed.append((doc_path.name, str(e)))

    print(f"\n{'='*60}")
    print(f"✅ Uploaded: {len(uploaded)}/{len(docs)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for name, err in failed:
            print(f"   - {name}: {err}")

    # Now auto-approve them
    if uploaded:
        print(f"\n🔐 Auto-approving {len(uploaded)} documents...")
        approve_all(base_url, admin_password, uploaded)


def approve_all(base_url: str, admin_password: str, filenames: list):
    """Auto-approve uploaded documents with proper session handling."""

    try:
        session = requests.Session()

        # Login with allow_redirects=False to inspect the raw response
        login_url = urljoin(base_url, "/admin/login")
        print(f"  Logging in to {login_url}...")

        resp = session.post(login_url,
                           data={"password": admin_password},
                           timeout=30,
                           allow_redirects=False)

        # Check login response (should be 303 redirect)
        if resp.status_code == 401 or "Incorrect" in resp.text:
            print("❌ Admin password incorrect")
            return

        if resp.status_code not in (200, 303, 302):
            print(f"❌ Login failed with status {resp.status_code}")
            print(f"   Response: {resp.text[:200]}")
            return

        # Verify session cookie was set
        if not session.cookies:
            print("❌ No session cookie received from login")
            return

        print(f"✅ Admin login successful (cookies: {list(session.cookies.keys())})")

        # Get list of pending files to verify we're authenticated
        review_url = urljoin(base_url, "/admin/review")
        resp = session.get(review_url, timeout=30)

        if resp.status_code == 403 or resp.status_code == 401:
            print("❌ Session not authenticated - login cookie not working")
            return

        if resp.status_code != 200:
            print(f"❌ Could not access admin review page (status: {resp.status_code})")
            return

        print("✅ Admin session authenticated")

        # Approve each file
        approve_url = urljoin(base_url, "/admin/approve")
        approved = 0

        for filename in filenames:
            try:
                # Use allow_redirects=False to see the 303 response
                resp = session.post(approve_url,
                                   data={"filename": filename},
                                   timeout=60,
                                   allow_redirects=False)

                # Success responses: 303 (redirect) or 200
                if resp.status_code in (200, 303):
                    print(f"  ✅ Approved: {filename}")
                    approved += 1
                elif resp.status_code == 404:
                    print(f"  ⚠️  {filename}: File not found in pending (already approved?)")
                elif resp.status_code == 403:
                    print(f"  ❌ {filename}: Not authenticated")
                else:
                    print(f"  ⚠️  {filename}: Status {resp.status_code}")
            except Exception as e:
                print(f"  ❌ {filename}: {e}")

        print(f"\n✅ Successfully approved {approved}/{len(filenames)} documents")
        if approved == len(filenames):
            print("🎉 All documents are now in the knowledge base!")
        else:
            print(f"⚠️  {len(filenames) - approved} documents were not approved")

    except Exception as e:
        print(f"❌ Approval failed: {e}")
        import traceback
        traceback.print_exc()
        print("   You can manually approve documents in the Admin panel")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 bulk_upload.py <railway-url> [admin-password]")
        print("\nExample:")
        print("  python3 bulk_upload.py https://app-prod-1234.railway.app vifc-admin-2026")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    admin_password = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ADMIN_PASSWORD", "vifc-admin-2026")

    print(f"🚀 Starting bulk upload to {base_url}\n")
    bulk_upload(base_url, admin_password)
