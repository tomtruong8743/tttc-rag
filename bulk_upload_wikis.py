#!/usr/bin/env python3
"""
Bulk upload wiki files to Railway VIFC Knowledge Assistant.

Usage:
    python3 bulk_upload_wikis.py https://your-railway-url.app

This script:
1. Reads all .md files from wiki/ folder
2. Uploads them to the remote server
3. Auto-approves them
"""

import sys
import os
from pathlib import Path
import requests
from urllib.parse import urljoin

# Config
WIKI_DIR = Path(__file__).parent / "wiki"

def bulk_upload_wikis(base_url: str, admin_password: str):
    """Upload all wiki files from wiki/ to the server."""

    if not WIKI_DIR.exists():
        print(f"❌ No wiki folder found: {WIKI_DIR}")
        return

    # Get all markdown files from wiki folder and subfolders
    wiki_files = list(WIKI_DIR.rglob("*.md"))

    if not wiki_files:
        print(f"❌ No markdown files found in {WIKI_DIR}")
        return

    print(f"📚 Found {len(wiki_files)} wiki files to upload\n")

    uploaded = []
    failed = []

    for i, wiki_path in enumerate(wiki_files, 1):
        # Show relative path for clarity
        rel_path = wiki_path.relative_to(WIKI_DIR)
        print(f"[{i}/{len(wiki_files)}] Uploading {rel_path}...", end=" ")

        try:
            # Upload as markdown file
            with open(wiki_path, "rb") as f:
                files = {"file": (wiki_path.name, f, "text/markdown")}
                data = {"submitter_email": "wiki-import@vifc.local",
                        "description": f"Wiki: {rel_path}"}

                upload_url = urljoin(base_url, "/upload")
                resp = requests.post(upload_url, files=files, data=data, timeout=60)
                resp.raise_for_status()

            print("✅ Uploaded")
            uploaded.append(wiki_path.name)

        except Exception as e:
            print(f"❌ Failed: {e}")
            failed.append((wiki_path.name, str(e)))

    print(f"\n{'='*60}")
    print(f"✅ Uploaded: {len(uploaded)}/{len(wiki_files)}")
    if failed:
        print(f"❌ Failed: {len(failed)}")
        for name, err in failed:
            print(f"   - {name}: {err}")

    # Auto-approve them
    if uploaded:
        print(f"\n🔐 Auto-approving {len(uploaded)} wiki files...")
        approve_all(base_url, admin_password, uploaded)


def approve_all(base_url: str, admin_password: str, filenames: list):
    """Auto-approve uploaded wiki files with proper session handling."""

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
            return

        # Verify session cookie was set
        if not session.cookies:
            print("❌ No session cookie received from login")
            return

        print("✅ Admin login successful")

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
                    print(f"  ⚠️  {filename}: File not found (already approved?)")
                elif resp.status_code == 403:
                    print(f"  ❌ {filename}: Not authenticated")
                else:
                    print(f"  ⚠️  {filename}: Status {resp.status_code}")
            except Exception as e:
                print(f"  ❌ {filename}: {e}")

        print(f"\n✅ Successfully approved {approved}/{len(filenames)} wiki files")
        if approved == len(filenames):
            print("📚 All wikis are now part of the knowledge base!")
        else:
            print(f"⚠️  {len(filenames) - approved} files were not approved")

    except Exception as e:
        print(f"❌ Approval failed: {e}")
        import traceback
        traceback.print_exc()
        print("   You can manually approve files in the Admin panel")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 bulk_upload_wikis.py <railway-url> [admin-password]")
        print("\nExample:")
        print("  python3 bulk_upload_wikis.py https://tttc-rag-production.up.railway.app vifc-admin-2026")
        sys.exit(1)

    base_url = sys.argv[1].rstrip("/")
    admin_password = sys.argv[2] if len(sys.argv) > 2 else os.environ.get("ADMIN_PASSWORD", "vifc-admin-2026")

    print(f"🚀 Starting wiki upload to {base_url}\n")
    bulk_upload_wikis(base_url, admin_password)
