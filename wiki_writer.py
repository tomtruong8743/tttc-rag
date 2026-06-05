"""
Wiki writer: generate or update a Markdown wiki page for a given topic.

Usage:
    python wiki_writer.py "Machine Learning"
    python wiki_writer.py "Machine Learning" --top-k 8
    python wiki_writer.py "Machine Learning" --question "What is supervised learning?"
"""

import argparse
import os
import re
import sys
from datetime import date
from pathlib import Path

import llm_client
from retrieval import retrieve, format_citation
WIKI_DIR = Path("wiki")
MAX_CONTEXT_CHARS = 12_000

WIKI_FOLDERS = ["inbox", "projects", "research", "reference", "meetings", "legal_framework"]


def topic_to_filename(topic: str, folder: str = "inbox") -> Path:
    slug = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    slug = re.sub(r"[\s]+", "_", slug)
    target_dir = WIKI_DIR / folder
    target_dir.mkdir(parents=True, exist_ok=True)
    return target_dir / f"{slug}.md"


def find_existing_page(topic: str):
    """Search all wiki folders for an existing page for this topic."""
    slug = re.sub(r"[^\w\s-]", "", topic).strip().lower()
    slug = re.sub(r"[\s]+", "_", slug)
    for folder in ["inbox"] + WIKI_FOLDERS:
        candidate = WIKI_DIR / folder / f"{slug}.md"
        if candidate.exists():
            return candidate
    return None


def build_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[{i}] Source: {format_citation(chunk)}\n{chunk['text'].strip()}")
    return "\n\n---\n\n".join(parts)


GENERATE_PROMPT = """\
You are a technical wiki author. Using ONLY the source excerpts provided, write a \
wiki page for the topic "{topic}". Follow this exact structure:

# {topic}

## Summary
One short paragraph summarising the topic. When you mention any concept, decree, policy, \
or topic that could have its own wiki page, wrap it in Obsidian wikilinks like [[Decree 323 Establishment of TTTC]] \
or [[Tax Incentives and Exemptions]].

## Key Points
- Bullet list of the most important facts. Add an inline citation [N] after each point.
- Wrap key terms and related topics in [[wikilinks]] where appropriate.

## Definitions
A short glossary of key terms. Each entry: **term** — definition [N].
Wrap each term in [[wikilinks]] if it is likely to have its own page.

## Related Topics
A bullet list of related subjects. Each item MUST be wrapped in a [[wikilink]], e.g.:
- [[Decree 324 Financial Policies]]
- [[Foreign Investment Rules in TTTC]]

## Sources
Numbered list matching the inline citations used above.

Known pages in this wiki (always wikilink these when mentioned):
{known_pages}

Rules:
- Use ONLY information from the excerpts. Do not add outside knowledge.
- If the excerpts do not cover a section, write "Not covered in source documents." for that section.
- Mark uncertain information with "(uncertain)".
- Do NOT include a "Last Updated" or "Update Log" section — those are added automatically.
"""

UPDATE_WIKILINK_PROMPT = """\
You are a technical wiki author updating an existing page for "{topic}". \
New source excerpts are provided. Update the page and add or improve [[wikilinks]] \
wherever a concept, decree, policy, or topic is mentioned that could have its own page.

Follow the same structure as the existing page. Do NOT include a "Last Updated" or \
"Update Log" section — those are added automatically.

Known pages in this wiki (always wikilink these when mentioned):
{known_pages}

Rules:
- Only add information supported by the provided excerpts.
- Mark uncertain information with "(uncertain)".
- Keep inline citations consistent with the Sources section.
- Every item in Related Topics must be a [[wikilink]].
"""


def extract_update_log(existing: str) -> str:
    """Pull the existing update log block out of a wiki page, if present."""
    match = re.search(r"(## Update Log\n[\s\S]+)$", existing)
    return match.group(1) if match else "## Update Log\n"


def strip_update_log(content: str) -> str:
    return re.sub(r"\n*## Update Log\n[\s\S]+$", "", content).rstrip()


def append_update_entry(log: str, note: str) -> str:
    today = date.today().isoformat()
    entry = f"- **{today}**: {note}"
    return log.rstrip() + "\n" + entry + "\n"


def get_known_pages() -> str:
    """Return a formatted list of all existing wiki page titles for wikilink hints."""
    pages = [p for p in WIKI_DIR.glob("**/*.md") if p.name != ".gitkeep"]
    titles = [p.stem.replace("_", " ").title() for p in pages]
    return "\n".join(f"- [[{t}]]" for t in sorted(titles)) or "- (none yet)"


def generate_wiki_page(topic: str, chunks: list[dict]) -> str:
    context = build_context(chunks)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[context truncated]"

    prompt = GENERATE_PROMPT.format(topic=topic, known_pages=get_known_pages())
    user_message = f"Source excerpts:\n\n{context}\n\nWrite the wiki page now."
    return llm_client.chat(system=prompt, user=user_message, max_tokens=2048)



def update_wiki_page(topic: str, existing_body: str, chunks: list[dict]) -> str:
    context = build_context(chunks)
    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[context truncated]"

    system = UPDATE_WIKILINK_PROMPT.format(topic=topic, known_pages=get_known_pages())
    user_message = (
        f"Existing wiki page:\n\n{existing_body}\n\n"
        f"---\n\nNew source excerpts:\n\n{context}\n\n"
        f"Write the updated wiki page now."
    )
    return llm_client.chat(system=system, user=user_message, max_tokens=2048)


def save_wiki_page(topic: str, chunks: list[dict], folder: str = "inbox") -> Path:
    WIKI_DIR.mkdir(exist_ok=True)

    # Check all folders for an existing page before creating a new one
    existing_path = find_existing_page(topic)
    today = date.today().isoformat()

    if existing_path:
        page_path = existing_path
        existing = page_path.read_text(encoding="utf-8")
        update_log = extract_update_log(existing)
        existing_body = strip_update_log(existing)

        print(f"[wiki] Page exists — updating: {page_path}")
        new_body = update_wiki_page(topic, existing_body, chunks)
        update_log = append_update_entry(update_log, "Updated with new source retrieval.")
        action = "updated"
    else:
        page_path = topic_to_filename(topic, folder)
        print(f"[wiki] Creating new page: {page_path}")
        new_body = generate_wiki_page(topic, chunks)
        update_log = append_update_entry("## Update Log\n", "Page created.")
        action = "created"

    last_updated = f"\n\n*Last updated: {today}*"
    final = f"{new_body}{last_updated}\n\n{update_log}"
    page_path.write_text(final, encoding="utf-8")
    print(f"[wiki] Page {action}: {page_path}")
    return page_path


def main():
    parser = argparse.ArgumentParser(description="Generate or update a wiki page for a topic.")
    parser.add_argument("topic", help="Topic to write a wiki page about")
    parser.add_argument("--folder", default="inbox", choices=WIKI_FOLDERS,
                        help="Wiki folder to save the page in (default: inbox)")
    parser.add_argument("--top-k", type=int, default=6, help="Chunks to retrieve (default: 6)")
    parser.add_argument("--question", default=None, help="Optional retrieval query (defaults to topic name)")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY environment variable is not set.")
        sys.exit(1)

    query = args.question or args.topic
    print(f"[wiki] Retrieving chunks for: {query!r}")
    chunks = retrieve(query, top_k=args.top_k)

    if not chunks:
        print("[error] No chunks retrieved. Have you run `python ingest.py` first?")
        sys.exit(1)

    path = save_wiki_page(args.topic, chunks, folder=args.folder)
    print(f"\n[done] Wiki page saved to {path}")


if __name__ == "__main__":
    main()
