"""
Bulk wiki generation script.
Generates one wiki page per topic, organised into the correct folders.

Usage:
    python3 bulk_wiki.py
    python3 bulk_wiki.py --dry-run   # preview topics and folders without generating
    python3 bulk_wiki.py --start 47  # resume from index 47 after a failure
"""

import argparse
import os
import sys
from retrieval import retrieve
from wiki_writer import save_wiki_page

# (topic, folder) pairs
TOPICS = [
    # ── Overview → inbox ────────────────────────────────────────────────────
    ("What Is the Vietnam International Financial Centre",                      "inbox"),
    ("Why Was the Vietnam International Financial Centre Created",              "inbox"),
    ("Main Goals of the Vietnam International Financial Centre",               "inbox"),
    ("Problems the Vietnam International Financial Centre Is Solving",         "inbox"),
    ("Main Functions of the Vietnam International Financial Centre",           "inbox"),
    ("Cities Involved in the Vietnam International Financial Centre",          "inbox"),
    ("Target Participants of the Vietnam International Financial Centre",      "inbox"),
    ("Vietnam International Financial Centre for Investment Banking Interns",  "inbox"),

    # ── Legal framework → legal_framework ───────────────────────────────────
    ("Legal Documents Establishing the Vietnam International Financial Centre","legal_framework"),
    ("Main Decrees Related to the Vietnam International Financial Centre",     "legal_framework"),
    ("Decree 323 Establishment of TTTC",                                       "legal_framework"),
    ("Decree 324 Financial Policies of TTTC",                                  "legal_framework"),
    ("Decree 325 Labor and Social Security in TTTC",                           "legal_framework"),
    ("Decree 326 Land and Environment in TTTC",                                "legal_framework"),
    ("Decree 330 Commodities Exchange in TTTC",                                "legal_framework"),
    ("Regulatory Bodies Supervising the Vietnam International Financial Centre","legal_framework"),
    ("Special Legal Mechanisms in the Vietnam International Financial Centre", "legal_framework"),
    ("Legal Protections for Investors in the Vietnam International Financial Centre","legal_framework"),
    ("Dispute Resolution in the Vietnam International Financial Centre",       "legal_framework"),
    ("Arbitration in the Vietnam International Financial Centre",              "legal_framework"),
    ("How Disputes Are Handled in the Vietnam International Financial Centre", "legal_framework"),
    ("Investor Protection Mechanisms in the Vietnam International Financial Centre","legal_framework"),
    ("Legal Protections for Foreign Financial Institutions in TTTC",          "legal_framework"),
    ("Why Dispute Resolution Matters for Investment Banks in TTTC",           "legal_framework"),
    ("Anti Money Laundering Rules in the Vietnam International Financial Centre","legal_framework"),
    ("Compliance Requirements in the Vietnam International Financial Centre",  "legal_framework"),
    ("KYC Requirements in the Vietnam International Financial Centre",         "legal_framework"),
    ("Reporting Obligations for Financial Institutions in TTTC",              "legal_framework"),
    ("Risk Management Requirements in the Vietnam International Financial Centre","legal_framework"),
    ("Supervision Mechanisms in the Vietnam International Financial Centre",   "legal_framework"),
    ("Compliance Risks for Investment Banks in TTTC",                         "legal_framework"),
    ("AML and Compliance Summary for Investment Banks in TTTC",               "legal_framework"),

    # ── Research → research ─────────────────────────────────────────────────
    ("Investment Banking Opportunities in the Vietnam International Financial Centre","research"),
    ("How Investment Banks Can Participate in the Vietnam International Financial Centre","research"),
    ("Financial Services Investment Banks Can Provide in TTTC",               "research"),
    ("Capital Raising in the Vietnam International Financial Centre",          "research"),
    ("Mergers and Acquisitions in the Vietnam International Financial Centre", "research"),
    ("Equity Capital Markets in the Vietnam International Financial Centre",   "research"),
    ("Debt Capital Markets in the Vietnam International Financial Centre",     "research"),
    ("Vietnamese Companies Accessing International Capital via TTTC",         "research"),
    ("Role of Foreign Financial Institutions in the Vietnam International Financial Centre","research"),
    ("Role of Domestic Banks and Securities Firms in TTTC",                   "research"),
    ("Capital Markets in the Vietnam International Financial Centre",          "research"),
    ("Developing Vietnam Capital Markets Through TTTC",                        "research"),
    ("Capital Market Activities Allowed in the Vietnam International Financial Centre","research"),
    ("How Companies Raise Capital Through the Vietnam International Financial Centre","research"),
    ("Bond Issuance Opportunities in the Vietnam International Financial Centre","research"),
    ("Equity Issuance Opportunities in the Vietnam International Financial Centre","research"),
    ("Attracting Foreign Investors to Vietnam Capital Markets via TTTC",       "research"),
    ("Securities Activities in the Vietnam International Financial Centre",    "research"),
    ("Financial Products and Instruments in the Vietnam International Financial Centre","research"),
    ("Banking Activities Allowed in the Vietnam International Financial Centre","research"),
    ("Types of Financial Institutions in the Vietnam International Financial Centre","research"),
    ("Rules for Banks Operating in the Vietnam International Financial Centre","research"),
    ("Foreign Banks in the Vietnam International Financial Centre",            "research"),
    ("Domestic Banks in the Vietnam International Financial Centre",           "research"),
    ("Licenses and Approvals for Financial Institutions in TTTC",             "research"),
    ("Financial Services in the Vietnam International Financial Centre",       "research"),
    ("Membership Requirements for the Vietnam International Financial Centre", "research"),
    ("Benefits for Foreign Investors in the Vietnam International Financial Centre","research"),
    ("Incentives for Foreign Investors in the Vietnam International Financial Centre","research"),
    ("Restrictions on Foreign Investors in the Vietnam International Financial Centre","research"),
    ("How the Vietnam International Financial Centre Attracts Foreign Capital", "research"),
    ("Foreign Investor Participation in Vietnam Financial Markets via TTTC",   "research"),
    ("Foreign Ownership Rules in the Vietnam International Financial Centre",  "research"),
    ("Protections for Foreign Investors in the Vietnam International Financial Centre","research"),
    ("Risks for Foreign Investors in the Vietnam International Financial Centre","research"),
    ("Tax Incentives in the Vietnam International Financial Centre",           "research"),
    ("Corporate Income Tax Incentives in the Vietnam International Financial Centre","research"),
    ("Personal Income Tax Incentives in the Vietnam International Financial Centre","research"),
    ("Tax Benefits for Workers and Experts in TTTC",                          "research"),
    ("Tax Benefits for Companies in the Vietnam International Financial Centre","research"),
    ("Conditions for Tax Incentives in the Vietnam International Financial Centre","research"),
    ("Expiry of Tax Incentives in the Vietnam International Financial Centre", "research"),
    ("Tax Incentive Summary for Investment Banks in TTTC",                    "research"),
    ("Foreign Exchange Rules in the Vietnam International Financial Centre",   "research"),
    ("Foreign Currency Transactions in the Vietnam International Financial Centre","research"),
    ("Capital Movement Rules in the Vietnam International Financial Centre",   "research"),
    ("Transferring Capital Into and Out of the Vietnam International Financial Centre","research"),
    ("Cross Border Payments in the Vietnam International Financial Centre",    "research"),
    ("Profit Repatriation in the Vietnam International Financial Centre",      "research"),
    ("International Capital Flows in the Vietnam International Financial Centre","research"),
    ("Why Foreign Exchange Rules Matter for Investment Banks in TTTC",        "research"),
    ("Fund Management in the Vietnam International Financial Centre",          "research"),
    ("Asset Managers in the Vietnam International Financial Centre",           "research"),
    ("Investment Funds in the Vietnam International Financial Centre",         "research"),
    ("Private Equity in the Vietnam International Financial Centre",           "research"),
    ("Venture Capital in the Vietnam International Financial Centre",          "research"),
    ("Rules for Fund Managers in the Vietnam International Financial Centre",  "research"),
    ("Attracting Global Asset Managers to the Vietnam International Financial Centre","research"),
    ("Investment Bank Services for Funds in the Vietnam International Financial Centre","research"),
    ("M&A Relevance in the Vietnam International Financial Centre",            "research"),
    ("Cross Border M&A in the Vietnam International Financial Centre",         "research"),
    ("Legal and Financial Policies Affecting M&A in TTTC",                    "research"),
    ("Corporate Advisory Opportunities in the Vietnam International Financial Centre","research"),
    ("How Investment Banks Can Advise Clients on TTTC",                       "research"),
    ("M&A Risks in the Vietnam International Financial Centre",                "research"),
    ("M&A Implications of the Vietnam International Financial Centre Framework","research"),
    ("Labor and Employment Rules in the Vietnam International Financial Centre","research"),
    ("Policies for Foreign Experts in the Vietnam International Financial Centre","research"),
    ("Incentives for High Quality Workers in the Vietnam International Financial Centre","research"),
    ("Immigration and Residency Policies for TTTC Workers",                   "research"),
    ("Attracting International Financial Talent to TTTC",                     "research"),
    ("Why Talent Policies Matter for Investment Banks in TTTC",               "research"),
    ("Land Use Policies in the Vietnam International Financial Centre",        "research"),
    ("Real Estate and Office Policies in the Vietnam International Financial Centre","research"),
    ("Infrastructure Planned for the Vietnam International Financial Centre",  "research"),
    ("Location of the Vietnam International Financial Centre",                 "research"),
    ("Facilities and Zones in the Vietnam International Financial Centre",     "research"),
    ("Why Physical Location Matters for Banks in TTTC",                       "research"),
    ("Ho Chi Minh City vs Da Nang in the Vietnam International Financial Centre","research"),
    ("Domestic vs Foreign Institutions in the Vietnam International Financial Centre","research"),
    ("Tax vs Regulatory Incentives in the Vietnam International Financial Centre","research"),
    ("Opportunities for Banks Asset Managers Fintech and Investment Banks in TTTC","research"),
    ("Strongest Advantages of TTTC for Foreign Financial Institutions",       "research"),
    ("Biggest Risks for Investment Banks in the Vietnam International Financial Centre","research"),
    ("Information Missing from TTTC Source Documents",                        "research"),
    ("Follow Up Questions for Investment Banks Entering TTTC",                "research"),

    # ── Reference → reference ───────────────────────────────────────────────
    ("Bilingual Glossary of Key TTTC Terms",                                   "reference"),
    ("Important Vietnamese Financial Terms in TTTC",                           "reference"),
    ("Investment Banking Terms in TTTC Documents",                             "reference"),
    ("Glossary for Investment Banking Interns Working with TTTC",              "reference"),
    ("Vietnamese Legal and Financial Terms in TTTC Defined in English",        "reference"),
    ("Trung Tam Tai Chinh Quoc Te Definition and Importance",                  "reference"),
    ("Thi Truong Von in the Context of TTTC",                                  "reference"),
    ("Ngoai Hoi in the Context of TTTC",                                       "reference"),
    ("Phong Chong Rua Tien in the Context of TTTC",                            "reference"),
    ("Co Che Thu Nghiem Co Kiem Soat in the Context of TTTC",                  "reference"),

    # ── Projects → projects ─────────────────────────────────────────────────
    ("Due Diligence Checklist for Investment Banks Evaluating TTTC",           "projects"),
    ("Legal Due Diligence Questions for the Vietnam International Financial Centre","projects"),
    ("Regulatory Due Diligence Questions for the Vietnam International Financial Centre","projects"),
    ("Tax Due Diligence Questions for the Vietnam International Financial Centre","projects"),
    ("Compliance Due Diligence Questions for the Vietnam International Financial Centre","projects"),
    ("Operational Due Diligence Questions for the Vietnam International Financial Centre","projects"),
    ("Market Opportunity Due Diligence Questions for TTTC",                    "projects"),
    ("What Investment Banks Need Before Advising Clients on TTTC",             "projects"),
    ("Due Diligence Topics for Investment Banks in TTTC",                      "projects"),
    ("Investment Banking Perspective on the Vietnam International Financial Centre","projects"),
]


def main():
    parser = argparse.ArgumentParser(description="Bulk generate wiki pages for TTTC topics.")
    parser.add_argument("--dry-run", action="store_true", help="Print topics without generating")
    parser.add_argument("--top-k", type=int, default=6)
    parser.add_argument("--start", type=int, default=0, help="Resume from this index after a failure")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY is not set.")
        sys.exit(1)

    total = len(TOPICS)
    print(f"{'DRY RUN — ' if args.dry_run else ''}{total} topics to generate\n")

    folder_counts = {}
    for topic, folder in TOPICS:
        folder_counts[folder] = folder_counts.get(folder, 0) + 1

    print("Breakdown by folder:")
    for folder, count in sorted(folder_counts.items()):
        print(f"  wiki/{folder}/  →  {count} pages")
    print()

    for i, (topic, folder) in enumerate(TOPICS):
        if i < args.start:
            continue

        print(f"[{i+1}/{total}] [{folder}] {topic}")
        if args.dry_run:
            continue

        try:
            chunks = retrieve(topic, top_k=args.top_k)
            if not chunks:
                print(f"  [skip] No chunks retrieved.")
                continue
            save_wiki_page(topic, chunks, folder=folder)
        except Exception as e:
            print(f"  [error] {e}")
            print(f"  Tip: re-run with --start {i} to resume from here.")
            sys.exit(1)

    if not args.dry_run:
        print(f"\n[done] {total} wiki pages generated.")


if __name__ == "__main__":
    main()
