"""Fix BPMN mermaid diagrams to be mmdc-compatible."""
import re
from pathlib import Path

files = list(Path("wiki/projects").glob("bpmn_*.md"))

for f in files:
    content = f.read_text(encoding="utf-8")

    # Remove the empty subgraph END wrapper, keep just the node
    content = re.sub(
        r'\n\s+subgraph END \[""\]\n\s+(E\([^)]+\))\n\s+end\n',
        r'\n    \1\n',
        content
    )

    # Fix start node — use plain ((Start)) double circle
    content = content.replace('S([START])', 'S((Start))')
    content = content.replace('S([○ Start])', 'S((Start))')

    # Fix end node — use plain ((End))
    content = content.replace('E([END])', 'E((End))')

    # Fix styling for S and E nodes
    content = content.replace(
        'style S fill:#fff,stroke:#1c2f72,stroke-width:3px',
        'style S fill:#ffffff,stroke:#1c2f72,stroke-width:3px,color:#1c2f72'
    )
    content = content.replace(
        'style E fill:#1c2f72,stroke:#1c2f72,color:#fff',
        'style E fill:#1c2f72,stroke:#1c2f72,color:#ffffff'
    )

    f.write_text(content, encoding="utf-8")
    print(f"Fixed: {f.name}")

print("Done.")
