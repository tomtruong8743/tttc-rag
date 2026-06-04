"""
Merge process map wiki content into the corresponding BPMN wiki files.
Extracts non-flowchart sections from process maps and appends them
to the BPMN wikis under a new heading.
"""

import re
from pathlib import Path
from datetime import date

WIKI = Path("wiki/projects")
TODAY = date.today().isoformat()

PAIRS = [
    ("bpmn_foreign_company_cooperation_with_vifc.md",
     "process_map_how_foreign_companies_cooperate_with_vifc.md"),
    ("bpmn_bank_cooperation_with_vifc.md",
     "process_map_how_banks_cooperate_with_vifc.md"),
    ("bpmn_investment_bank_cooperation_with_vifc.md",
     "process_map_how_investment_banks_cooperate_with_vifc.md"),
    ("bpmn_import_export_cooperation_with_vifc.md",
     "process_map_how_import_export_companies_cooperate_with_vifc.md"),
    ("bpmn_fintech_cooperation_with_vifc.md",
     "process_map_how_fintech_companies_cooperate_with_vifc.md"),
]


def extract_non_flowchart_sections(content: str) -> str:
    """Remove the title, intro paragraph, and mermaid flowchart section.
    Keep everything else: stages, requirements, decrees table, benchmarking, related topics."""
    # Remove title (# line)
    content = re.sub(r'^# .+\n', '', content, count=1)
    # Remove intro paragraph before first ##
    content = re.sub(r'^.*?(?=^##)', '', content, count=1, flags=re.DOTALL)
    # Remove the flowchart section (## ... Flowchart ... ```mermaid...```)
    content = re.sub(
        r'## .*?Flowchart.*?```mermaid.*?```\n',
        '', content, count=1, flags=re.DOTALL | re.IGNORECASE
    )
    # Remove Update Log and Last updated
    content = re.sub(r'\n\*Last updated:.*?\*\n', '\n', content)
    content = re.sub(r'\n## Update Log\n.*$', '', content, flags=re.DOTALL)
    return content.strip()


for bpmn_file, process_file in PAIRS:
    bpmn_path    = WIKI / bpmn_file
    process_path = WIKI / process_file

    if not bpmn_path.exists():
        print(f"[skip] Not found: {bpmn_file}")
        continue
    if not process_path.exists():
        print(f"[skip] Not found: {process_file}")
        continue

    bpmn_content    = bpmn_path.read_text(encoding="utf-8")
    process_content = process_path.read_text(encoding="utf-8")

    extracted = extract_non_flowchart_sections(process_content)

    # Strip existing Update Log and Last updated from BPMN file
    bpmn_content = re.sub(r'\n\*Last updated:.*?\*\n', '\n', bpmn_content)
    bpmn_content = re.sub(r'\n## Update Log\n.*$', '', bpmn_content, flags=re.DOTALL)
    bpmn_content = bpmn_content.rstrip()

    merged = (
        bpmn_content
        + "\n\n---\n\n"
        + "## Detailed Process Information\n\n"
        + extracted
        + f"\n\n*Last updated: {TODAY}*\n\n"
        + f"## Update Log\n- **{TODAY}**: Merged detailed process map content.\n"
    )

    bpmn_path.write_text(merged, encoding="utf-8")
    print(f"✅ Merged into: {bpmn_file}")

print("\nDone.")
