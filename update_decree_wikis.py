"""
Update all decree and legal framework wiki pages with full document detail.
Run this after re-ingesting documents with OCR.

Usage:
    python3 update_decree_wikis.py
"""

import os
import sys
from retrieval import retrieve
from wiki_writer import save_wiki_page

FOLDER = "legal_framework"

DECREES = [
    ("Decree 323 Establishment of TTTC",           "Nghi dinh 323 thanh lap trung tam tai chinh"),
    ("Decree 324 Financial Policies of TTTC",      "Nghi dinh 324 chinh sach tai chinh uu dai thue"),
    ("Decree 325 Labor and Social Security in TTTC","Nghi dinh 325 lao dong viec lam an sinh xa hoi"),
    ("Decree 326 Land and Environment in TTTC",    "Nghi dinh 326 dat dai moi truong"),
    ("Decree 327 Immigration Policy",              "Nghi dinh 327 xuat nhap canh visa"),
    ("Decree 328 International Arbitration Center","Nghi dinh 328 trung tam trong tai quoc te"),
    ("Decree 329 Banking and Foreign Exchange",    "Nghi dinh 329 ngan hang cap phep ngoai hoi"),
    ("Decree 330 Commodities Exchange in TTTC",    "Nghi dinh 330 so giao dich hang hoa"),
    ("Legal Framework of TTTC",                    "khung phap ly trung tam tai chinh quoc te"),
    ("Main Decrees Related to the Vietnam International Financial Centre",
                                                   "cac nghi dinh lien quan den TTTC"),
    ("Legal Documents Establishing the Vietnam International Financial Centre",
                                                   "van ban phap ly thanh lap TTTC"),
    ("Special Legal Mechanisms in the Vietnam International Financial Centre",
                                                   "co che phap ly dac biet TTTC"),
    ("Legal Protections for Investors in the Vietnam International Financial Centre",
                                                   "bao ve nha dau tu trong TTTC"),
    ("Regulatory Bodies Supervising the Vietnam International Financial Centre",
                                                   "co quan quan ly giam sat TTTC"),
    ("Tax Incentives in the Vietnam International Financial Centre",
                                                   "uu dai thue suat mien giam thue TTTC"),
    ("Foreign Exchange Rules in the Vietnam International Financial Centre",
                                                   "quy dinh ngoai hoi giao dich ngoai te TTTC"),
    ("Anti Money Laundering Rules in the Vietnam International Financial Centre",
                                                   "phong chong rua tien TTTC"),
    ("Dispute Resolution in the Vietnam International Financial Centre",
                                                   "giai quyet tranh chap trong tai TTTC"),
]

def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY is not set.")
        sys.exit(1)

    total = len(DECREES)
    print(f"Updating {total} decree wiki pages with full OCR content...\n")

    for i, (topic, query) in enumerate(DECREES):
        print(f"[{i+1}/{total}] {topic}")
        try:
            chunks = retrieve(query, top_k=15)
            if not chunks:
                print(f"  [skip] No chunks retrieved.")
                continue
            print(f"  Retrieved {len(chunks)} chunks")
            save_wiki_page(topic, chunks, folder=FOLDER)
        except Exception as e:
            print(f"  [error] {e}")

    print(f"\n[done] All decree wikis updated.")

if __name__ == "__main__":
    main()
