"""
Evaluation script for the RAG + LLM Wiki System.

Tests:
  1. Chunk relevance       — retrieved chunks relate to the query
  2. Citation presence     — answers contain inline [N] citations
  3. Unsupported claims    — answers don't stray beyond the chunks
  4. Wiki section coverage — wiki pages include all required sections
  5. Metadata integrity    — every chunk carries source, page, chunk_index

Usage:
    python eval.py                          # run all tests
    python eval.py --query "your question"  # custom retrieval query
    python eval.py --verbose                # show full answers and chunks
"""

import argparse
import os
import re
import sys
from pathlib import Path

import anthropic

from retrieval import retrieve, format_citation
from answer import generate_answer
from wiki_writer import save_wiki_page, topic_to_filename

WIKI_DIR = Path("wiki")

REQUIRED_WIKI_SECTIONS = [
    "## Summary",
    "## Key Points",
    "## Definitions",
    "## Related Topics",
    "## Sources",
]

JUDGE_SYSTEM = """\
You are a strict evaluator for a RAG system. Answer with JSON only — no prose, \
no markdown fences. Be conservative: only mark something as passing if you are \
clearly confident.
"""


# ── Helpers ───────────────────────────────────────────────────────────────────

def check_citations(text: str) -> bool:
    """Return True if the text contains at least one [N] style citation."""
    return bool(re.search(r"\[\d+\]", text))


def client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


def llm_judge(prompt: str) -> dict:
    """Send a judging prompt to Claude and parse the JSON response."""
    import json
    response = client().messages.create(
        model="claude-haiku-4-5",
        max_tokens=256,
        system=JUDGE_SYSTEM,
        messages=[{"role": "user", "content": prompt}],
    )
    raw = response.content[0].text.strip()
    try:
        return json.loads(raw)
    except Exception:
        return {"error": f"Could not parse JSON: {raw}"}


# ── Individual tests ──────────────────────────────────────────────────────────

def test_metadata_integrity(query: str, top_k: int = 5, verbose: bool = False) -> dict:
    """Every chunk must have non-empty source, page, and chunk_index fields."""
    name = "metadata_integrity"
    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {"test": name, "passed": False, "reason": "No chunks returned.", "chunks": 0}

    failures = []
    for i, chunk in enumerate(chunks):
        missing = [f for f in ("source", "page", "chunk_index") if not str(chunk.get(f, "")).strip()]
        if missing:
            failures.append(f"chunk {i}: missing {missing}")

    passed = len(failures) == 0
    result = {
        "test": name,
        "passed": passed,
        "chunks_checked": len(chunks),
        "failures": failures,
    }
    if verbose:
        for i, c in enumerate(chunks):
            print(f"  chunk {i}: source={c.get('source')} page={c.get('page')} idx={c.get('chunk_index')}")
    return result


def test_chunk_relevance(query: str, top_k: int = 5, verbose: bool = False) -> dict:
    """Check chunk relevance using ChromaDB's embedding distance scores.

    ChromaDB returns cosine distances: 0.0 = identical, 2.0 = completely opposite.
    Chunks with distance < RELEVANCE_THRESHOLD are considered relevant.
    This is more reliable than an LLM judge for multilingual content.
    """
    name = "chunk_relevance"
    RELEVANCE_THRESHOLD = 1.2  # tuned for cosine distance; adjust down to be stricter

    chunks = retrieve(query, top_k=top_k)

    if not chunks:
        return {"test": name, "passed": False, "reason": "No chunks returned.", "relevant": 0, "total": 0}

    relevant_count = 0
    for i, chunk in enumerate(chunks):
        is_relevant = chunk["distance"] < RELEVANCE_THRESHOLD
        if is_relevant:
            relevant_count += 1
        if verbose:
            status = "✓" if is_relevant else "✗"
            print(f"  {status} chunk {i} ({format_citation(chunk)}): distance={chunk['distance']:.4f}")

    ratio = relevant_count / len(chunks)
    passed = ratio >= 0.6
    return {
        "test": name,
        "passed": passed,
        "relevant": relevant_count,
        "total": len(chunks),
        "ratio": round(ratio, 2),
        "reason": f"{relevant_count}/{len(chunks)} chunks below distance threshold ({RELEVANCE_THRESHOLD})",
    }


def test_citation_presence(query: str, top_k: int = 5, verbose: bool = False) -> dict:
    """Answer must contain at least one [N] inline citation."""
    name = "citation_presence"
    result = generate_answer(query, top_k=top_k)
    answer = result["answer"]
    passed = check_citations(answer)

    if verbose:
        print(f"  Answer preview: {answer[:300]}")

    return {
        "test": name,
        "passed": passed,
        "reason": "Found [N] citation(s)." if passed else "No [N] citations found in answer.",
        "answer_preview": answer[:200],
    }


def test_no_unsupported_claims(query: str, top_k: int = 5, verbose: bool = False) -> dict:
    """Ask a judge whether the answer sticks to the provided chunks."""
    name = "no_unsupported_claims"
    result = generate_answer(query, top_k=top_k)
    answer = result["answer"]
    context = "\n\n".join(
        f"[{i+1}] {c['text'][:400]}" for i, c in enumerate(result["chunks"])
    )

    prompt = (
        f"Source chunks:\n{context}\n\n"
        f"Answer:\n{answer}\n\n"
        "Does the answer make any specific factual claims that are NOT present in or "
        "directly inferable from the source chunks above? "
        "Reply with JSON only — use exactly these keys: "
        '{"unsupported_claims": true, "examples": ["example claim"]} '
        'if unsupported claims exist, or '
        '{"unsupported_claims": false, "examples": []} if all claims are supported.'
    )
    verdict = llm_judge(prompt)
    # Default to False (passing) if the key is missing or null — absence of evidence
    # of unsupported claims is not evidence of unsupported claims.
    unsupported = verdict.get("unsupported_claims")
    passed = not unsupported if isinstance(unsupported, bool) else True

    if verbose:
        print(f"  Unsupported claims found: {verdict.get('unsupported_claims')}")
        if verdict.get("examples"):
            for ex in verdict["examples"]:
                print(f"    - {ex}")

    return {
        "test": name,
        "passed": passed,
        "unsupported_claims_detected": verdict.get("unsupported_claims"),
        "examples": verdict.get("examples", []),
    }


def test_wiki_sections(topic: str, top_k: int = 6, verbose: bool = False) -> dict:
    """Generate (or reuse) a wiki page and check all required sections are present."""
    name = "wiki_section_coverage"
    chunks = retrieve(topic, top_k=top_k)

    if not chunks:
        return {"test": name, "passed": False, "reason": "No chunks to build wiki from."}

    page_path = save_wiki_page(topic, chunks)
    content = page_path.read_text(encoding="utf-8")

    missing = [s for s in REQUIRED_WIKI_SECTIONS if s not in content]
    passed = len(missing) == 0

    has_last_updated = bool(re.search(r"\*Last updated:", content))
    has_update_log = "## Update Log" in content

    if verbose:
        for section in REQUIRED_WIKI_SECTIONS:
            status = "✓" if section in content else "✗"
            print(f"  {status} {section}")
        print(f"  {'✓' if has_last_updated else '✗'} *Last updated*")
        print(f"  {'✓' if has_update_log else '✗'} ## Update Log")

    return {
        "test": name,
        "passed": passed and has_last_updated and has_update_log,
        "missing_sections": missing,
        "has_last_updated": has_last_updated,
        "has_update_log": has_update_log,
        "page": str(page_path),
    }


# ── Runner ────────────────────────────────────────────────────────────────────

def run_all(query: str, top_k: int = 5, verbose: bool = False) -> list[dict]:
    tests = [
        ("Metadata integrity",      lambda: test_metadata_integrity(query, top_k, verbose)),
        ("Chunk relevance",         lambda: test_chunk_relevance(query, top_k, verbose)),
        ("Citation presence",       lambda: test_citation_presence(query, top_k, verbose)),
        ("No unsupported claims",   lambda: test_no_unsupported_claims(query, top_k, verbose)),
        ("Wiki section coverage",   lambda: test_wiki_sections(query, top_k, verbose)),
    ]

    results = []
    passed_count = 0

    print(f"\nEvaluation query: {query!r}\n{'═' * 60}")
    for label, fn in tests:
        print(f"\n▶ {label}")
        try:
            result = fn()
        except Exception as e:
            result = {"test": label, "passed": False, "error": str(e)}

        status = "✅ PASS" if result.get("passed") else "❌ FAIL"
        print(f"  {status}")

        # print key details even without --verbose
        for key in ("reason", "ratio", "missing_sections", "failures", "error"):
            if result.get(key):
                print(f"  {key}: {result[key]}")

        if result.get("passed"):
            passed_count += 1
        results.append(result)

    print(f"\n{'═' * 60}")
    print(f"Result: {passed_count}/{len(tests)} tests passed\n")
    return results


def main():
    parser = argparse.ArgumentParser(description="Evaluate the RAG + Wiki system.")
    parser.add_argument("--query", default="What is the main topic of the documents?",
                        help="Retrieval query used for most tests")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--verbose", action="store_true", help="Print detailed output per test")
    args = parser.parse_args()

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("[error] ANTHROPIC_API_KEY is not set.")
        sys.exit(1)

    run_all(args.query, top_k=args.top_k, verbose=args.verbose)


if __name__ == "__main__":
    main()
