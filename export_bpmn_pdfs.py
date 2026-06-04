"""
Export BPMN wiki pages to PDF.
Extracts Mermaid diagrams, renders them as images via mmdc,
then builds a clean PDF using pandoc with the rendered images.

Usage:
    python3 export_bpmn_pdfs.py
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

BPMN_FILES = [
    "wiki/projects/bpmn_foreign_company_cooperation_with_vifc.md",
    "wiki/projects/bpmn_bank_cooperation_with_vifc.md",
    "wiki/projects/bpmn_investment_bank_cooperation_with_vifc.md",
    "wiki/projects/bpmn_import_export_cooperation_with_vifc.md",
    "wiki/projects/bpmn_fintech_cooperation_with_vifc.md",
]

OUTPUT_DIR = Path("word_exports")
MMDC      = "/opt/homebrew/bin/mmdc"
PANDOC    = "/opt/homebrew/bin/pandoc"
CONFIG    = "mmdc_config.json"

def check_tools():
    missing = []
    if not Path(MMDC).exists():
        missing.append(f"mmdc not found at {MMDC}")
    if not Path(PANDOC).exists():
        missing.append(f"pandoc not found at {PANDOC}")
    if missing:
        for m in missing:
            print(f"[error] {m}")
        sys.exit(1)

def render_mermaid_to_png(mermaid_code: str, output_path: Path) -> bool:
    """Render a Mermaid diagram to PNG using mmdc."""
    with tempfile.NamedTemporaryFile(suffix=".mmd", mode="w", delete=False) as f:
        f.write(mermaid_code)
        tmp = f.name
    try:
        result = subprocess.run(
            [MMDC, "-i", tmp, "-o", str(output_path),
             "-c", CONFIG, "-b", "white", "-w", "1200"],
            capture_output=True, text=True
        )
        return output_path.exists()
    except Exception as e:
        print(f"  [mmdc error] {e}")
        return False
    finally:
        os.unlink(tmp)

def process_file(md_path: Path):
    print(f"\n[export] {md_path.name}")
    content = md_path.read_text(encoding="utf-8")

    # Extract and replace each mermaid block with an image
    diagram_count = 0
    image_paths = []

    def replace_mermaid(match):
        nonlocal diagram_count
        diagram_count += 1
        mermaid_code = match.group(1).strip()
        img_path = OUTPUT_DIR / f"{md_path.stem}_diagram_{diagram_count}.png"

        print(f"  Rendering diagram {diagram_count}...")
        success = render_mermaid_to_png(mermaid_code, img_path)

        if success:
            image_paths.append(img_path)
            return f"![Process Diagram]({img_path.resolve()})\n"
        else:
            print(f"  [warn] Diagram {diagram_count} failed to render")
            return f"*[Diagram {diagram_count} — see Obsidian for rendered version]*\n"

    processed = re.sub(r"```mermaid\n(.*?)```", replace_mermaid, content, flags=re.DOTALL)

    # Remove Obsidian wikilinks [[...]] → plain text
    processed = re.sub(r"\[\[([^\]|]+)(?:\|[^\]]+)?\]\]", r"\1", processed)

    # Write processed markdown to temp file
    with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
        f.write(processed)
        tmp_md = f.name

    # Export to PDF via pandoc
    pdf_out = OUTPUT_DIR / f"{md_path.stem}.pdf"
    result = subprocess.run(
        [PANDOC, tmp_md, "-o", str(pdf_out),
         "--pdf-engine=xelatex",
         "-V", "geometry:margin=2cm",
         "-V", "mainfont=Arial",
         "-V", "fontsize=11pt"],
        capture_output=True, text=True
    )

    os.unlink(tmp_md)

    if result.returncode != 0:
        # Fallback: try without xelatex
        result2 = subprocess.run(
            [PANDOC, tmp_md if Path(tmp_md).exists() else "/dev/null",
             "--read=markdown", f"--metadata=title:{md_path.stem}"],
            capture_output=True, text=True
        )
        # Try wkhtmltopdf or basic pandoc
        with tempfile.NamedTemporaryFile(suffix=".md", mode="w", delete=False, encoding="utf-8") as f:
            f.write(processed)
            tmp_md2 = f.name
        result3 = subprocess.run(
            [PANDOC, tmp_md2, "-o", str(pdf_out),
             "-V", "geometry:margin=2cm",
             "-V", "fontsize=11pt"],
            capture_output=True, text=True
        )
        os.unlink(tmp_md2)
        if result3.returncode == 0:
            print(f"  ✅ PDF saved: {pdf_out.name}")
        else:
            print(f"  ❌ PDF failed: {result3.stderr[:200]}")
    else:
        print(f"  ✅ PDF saved: {pdf_out.name}")


def main():
    check_tools()
    OUTPUT_DIR.mkdir(exist_ok=True)

    for md_file in BPMN_FILES:
        path = Path(md_file)
        if path.exists():
            process_file(path)
        else:
            print(f"[skip] Not found: {md_file}")

    print(f"\n[done] PDFs saved to {OUTPUT_DIR}/")
    subprocess.run(["open", str(OUTPUT_DIR)])


if __name__ == "__main__":
    main()
