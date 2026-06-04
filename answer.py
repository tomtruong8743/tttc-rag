"""
Answer generation pipeline.

Flow for every question:
  1. Search existing wiki pages for a relevant one (semantic keyword match)
  2. If found      → answer from the wiki page content
  3. If not found  → retrieve chunks → generate wiki page → push to GitHub → answer from wiki

Usage:
    python answer.py "What is X?"
    python answer.py "What is X?" --top-k 8
"""

import argparse
import os
import subprocess
import sys
from pathlib import Path

import anthropic
from retrieval import retrieve, format_citation
from wiki_writer import save_wiki_page, WIKI_DIR

# Override with CLAUDE_MODEL env var to use a cheaper model e.g. claude-haiku-4-5
MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-4-6")
MAX_CONTEXT_CHARS = 40_000
WIKI_PUSH_ENABLED = True   # set False to skip git push


# ── Wiki search ───────────────────────────────────────────────────

def find_relevant_wiki(question: str):
    """
    Search all wiki pages for one relevant to the question.
    Uses the LLM to pick the best match from page titles, then returns
    (path, content) if a good match is found, else None.
    """
    pages = [p for p in WIKI_DIR.glob("**/*.md") if p.name != ".gitkeep" and p.stat().st_size > 100]
    if not pages:
        return None

    # Build a numbered list of titles for the LLM to choose from
    titles = [p.stem.replace("_", " ").title() for p in pages]
    numbered = "\n".join(f"{i+1}. {t}" for i, t in enumerate(titles))

    client = anthropic.Anthropic()
    response = client.messages.create(
        model="claude-haiku-4-5",
        max_tokens=64,
        system="You are a search assistant. Reply with only a number or 'none'.",
        messages=[{"role": "user", "content":
            f"Question: {question}\n\n"
            f"Which of these wiki pages is most relevant to answer this question?\n\n"
            f"{numbered}\n\n"
            f"Reply with just the number (e.g. '3') if one is clearly relevant, "
            f"or 'none' if no page is a good match."
        }],
    )
    choice = response.content[0].text.strip().lower()

    if choice == "none":
        return None
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(pages):
            path = pages[idx]
            content = path.read_text(encoding="utf-8")
            return path, content
    except ValueError:
        pass
    return None


# ── GitHub push ───────────────────────────────────────────────────

def push_wiki_to_github(page_path: Path):
    """Commit and push a newly created wiki page to GitHub."""
    wiki_dir = str(WIKI_DIR)
    try:
        subprocess.run(["git", "add", str(page_path)], cwd=wiki_dir, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", f"Auto: add wiki page {page_path.name}"],
            cwd=wiki_dir, check=True, capture_output=True
        )
        subprocess.run(["git", "push"], cwd=wiki_dir, check=True, capture_output=True)
        print(f"[wiki] Pushed {page_path.name} to GitHub.")
    except subprocess.CalledProcessError as e:
        print(f"[wiki] Git push skipped: {e.stderr.decode().strip() if e.stderr else e}")


# ── Context builders ──────────────────────────────────────────────

def build_chunk_context(chunks: list[dict]) -> str:
    parts = []
    for i, chunk in enumerate(chunks, start=1):
        parts.append(f"[{i}] Source: {format_citation(chunk)}\n{chunk['text'].strip()}")
    return "\n\n---\n\n".join(parts)


def build_wiki_context(wiki_path: Path, wiki_content: str) -> str:
    return f"[1] Source: Wiki — {wiki_path.stem.replace('_', ' ').title()}\n{wiki_content}"


# ── Prompts ───────────────────────────────────────────────────────

SYSTEM_PROMPT = """\
You are a detailed legal and policy research assistant. You are given source excerpts \
directly from official documents (marked [1], [2], etc.) and optionally a wiki summary \
for context.

Your job is to answer the question using the SOURCE EXCERPTS as the primary source of \
truth — not the wiki summary. The wiki summary is only provided for structural context.

Give a thorough, complete answer:
- Quote or closely paraphrase specific articles, clauses, numbers, percentages, \
  conditions, timeframes, and exceptions directly from the source excerpts.
- Do not generalise or vaguely describe what the document "covers" — state exactly \
  what it says.
- After each specific detail, add an inline citation [N] matching the excerpt number.
- Structure your answer with headings and bullet points for readability.
- If asked about a specific decree or policy, list every specific provision found \
  in the excerpts — do not stop at a summary.

Rules:
- Use ONLY the provided source excerpts for factual claims.
- If a detail is not in the excerpts, say so rather than generalising.
- Mark anything uncertain with "(uncertain)".
- Do NOT respond with vague phrases like "the decree covers X" — instead state \
  exactly what the decree says about X.
"""


# ── Main pipeline ─────────────────────────────────────────────────

def generate_answer(question: str, top_k: int = 15) -> dict:
    """
    Returns {answer, chunks, wiki_path, wiki_created}.
    """
    # Step 1: check for an existing relevant wiki page
    wiki_result = find_relevant_wiki(question)
    wiki_path = None
    wiki_created = False

    # Always retrieve raw chunks — these contain the full document detail
    chunks = retrieve(question, top_k=top_k)

    if wiki_result:
        wiki_path, wiki_content = wiki_result
        print(f"[answer] Found existing wiki: {wiki_path.name}")
        wiki_created = False
        source_label = f"Wiki: {wiki_path.stem.replace('_', ' ').title()}"
    else:
        if not chunks:
            return {
                "answer": "The source documents do not provide enough information to answer this question.",
                "chunks": [],
                "wiki_path": None,
                "wiki_created": False,
            }
        print(f"[answer] No wiki found — creating new page for: {question!r}")
        wiki_path = save_wiki_page(question, chunks, folder="inbox")
        wiki_created = True
        if WIKI_PUSH_ENABLED:
            push_wiki_to_github(wiki_path)
        wiki_content = wiki_path.read_text(encoding="utf-8")
        source_label = f"Wiki: {wiki_path.stem.replace('_', ' ').title()} (newly created)"

    # Build context: raw chunks first (full detail), then wiki as structure reference
    if chunks:
        chunk_context = build_chunk_context(chunks)
        wiki_header = f"\n\n---\n\n[WIKI SUMMARY for reference]\n{wiki_content[:3000]}"
        context = chunk_context + wiki_header
    else:
        # No chunks (shouldn't happen but fallback to wiki only)
        context = build_wiki_context(wiki_path, wiki_content)

    if len(context) > MAX_CONTEXT_CHARS:
        context = context[:MAX_CONTEXT_CHARS] + "\n\n[context truncated]"

    user_message = f"Source content:\n\n{context}\n\nQuestion: {question}"

    client = anthropic.Anthropic()
    response = client.messages.create(
        model=MODEL,
        max_tokens=4096,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": user_message}],
    )
    answer = response.content[0].text.strip()

    return {
        "answer": answer,
        "chunks": chunks,
        "wiki_path": wiki_path,
        "wiki_created": wiki_created,
        "source_label": source_label,
    }


def main():
    parser = argparse.ArgumentParser(description="Ask a question against your documents.")
    parser.add_argument("question", help="Question to answer")
    parser.add_argument("--top-k", type=int, default=8)
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY is not set.")
        sys.exit(1)

    print(f"\nQuestion: {args.question}\n{'─' * 60}")
    result = generate_answer(args.question, top_k=args.top_k)

    print(f"\nAnswer:\n{result['answer']}")

    if result.get("wiki_path"):
        status = "newly created" if result.get("wiki_created") else "existing"
        print(f"\n{'─' * 60}\nWiki page ({status}): {result['wiki_path']}")

    if result.get("chunks"):
        print(f"\nSource chunks used:")
        for i, chunk in enumerate(result["chunks"], start=1):
            print(f"  [{i}] {format_citation(chunk)}")


if __name__ == "__main__":
    main()
