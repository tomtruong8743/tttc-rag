"""
Generate comprehensive step-by-step onboarding wikis for organizations
considering working with VIFC.

Each wiki covers:
- Requirements VIFC needs from the organization
- Step-by-step process to work with VIFC
- Relevant decrees and legal references
- Cross-reference notes for comparison with other IFC centers

Usage:
    python3 create_partner_wikis.py
"""

import os
import sys
from retrieval import retrieve
from wiki_writer import save_wiki_page

FOLDER = "projects"

PARTNER_WIKIS = [

    # ── Banks — step-by-step onboarding guides (no existing equivalent) ──
    (
        "How Foreign Banks Can Work With VIFC — Step by Step Onboarding Guide",
        "foreign bank license requirements establishment VIFC ngan hang nuoc ngoai cap phep thanh lap"
    ),
    (
        "How Domestic Banks Can Work With VIFC — Step by Step Onboarding Guide",
        "domestic bank Vietnamese requirements VIFC ngan hang trong nuoc tham gia"
    ),

    # ── Investment Banks — step-by-step (existing pages cover activities, not process) ──
    (
        "How Investment Banks Can Work With VIFC — Step by Step Onboarding Guide",
        "investment bank securities firm requirements process VIFC cong ty chung khoan cap phep"
    ),

    # ── Import and Export — no existing coverage ────────────────────
    (
        "How Import and Export Companies Can Work With VIFC — Step by Step Onboarding Guide",
        "import export company trade requirements VIFC xuat nhap khau thuong mai hang hoa so giao dich"
    ),
    (
        "Customs and Import Export Regulations at VIFC",
        "customs regulations import export VIFC hai quan xuat nhap khau thu tuc thue quan"
    ),

    # ── Fintech — no existing coverage ──────────────────────────────
    (
        "How Fintech Companies Can Work With VIFC — Step by Step Onboarding Guide",
        "fintech technology company sandbox requirements VIFC co che thu nghiem co kiem soat"
    ),

    # ── Insurance — no existing coverage ────────────────────────────
    (
        "How Insurance Companies Can Work With VIFC — Step by Step Onboarding Guide",
        "insurance company requirements license establishment VIFC bao hiem cap phep"
    ),

    # ── General foreign company setup — no existing step-by-step ────
    (
        "How Foreign Companies Can Establish Operations at VIFC — Step by Step",
        "foreign company establishment setup requirements VIFC thanh lap cong ty nuoc ngoai thu tuc dang ky"
    ),

    # ── Cross-reference benchmarking — no existing equivalent ───────
    (
        "VIFC Onboarding Requirements — IFC Benchmarking and Cross-Reference Guide",
        "requirements process regulations VIFC so sanh trung tam tai chinh quoc te Singapore Hong Kong Dubai"
    ),
]


DETAILED_PROMPT_OVERRIDE = """
For this wiki page, structure the content as follows:

1. **Overview** — What type of organization this covers and why VIFC is relevant to them
2. **Requirements from the Organization** — Exact documents, capital minimums, licenses, qualifications VIFC requires
3. **Step-by-Step Process** — Numbered steps from initial application to full operation
4. **Key Decrees and Legal Basis** — Which specific decrees govern this organization type
5. **Tax and Financial Incentives Available** — Specific incentives this type of organization can access
6. **Ongoing Compliance Obligations** — What the organization must do after establishment
7. **Cross-Reference Notes** — Fields left for comparison with other IFC centers (Hong Kong, Singapore, Dubai)
8. **Related Topics** — Wikilinks to related pages

Be as specific as possible — include article numbers, deadlines, capital amounts, and exact procedure names from the source documents.
"""


def main():
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY is not set.")
        sys.exit(1)

    # Inject the detailed structure prompt into wiki_writer temporarily
    import wiki_writer
    original_prompt = wiki_writer.GENERATE_PROMPT

    wiki_writer.GENERATE_PROMPT = original_prompt.replace(
        "Rules:",
        DETAILED_PROMPT_OVERRIDE + "\nRules:"
    )

    total = len(PARTNER_WIKIS)
    print(f"Generating {total} partner onboarding wikis into wiki/{FOLDER}/\n")

    for i, (topic, query) in enumerate(PARTNER_WIKIS):
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
            print(f"  Tip: re-run with --start {i} to resume.")
            # Restore prompt before exit
            wiki_writer.GENERATE_PROMPT = original_prompt
            sys.exit(1)

    # Restore original prompt
    wiki_writer.GENERATE_PROMPT = original_prompt
    print(f"\n[done] {total} partner wikis generated in wiki/{FOLDER}/")
    print("\nNext: push to GitHub:")
    print("  cd wiki && git add . && git commit -m 'Add partner onboarding wikis' && git push")


if __name__ == "__main__":
    main()
