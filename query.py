"""
CLI script to test retrieval.

Usage:
    python query.py "Your question here"
    python query.py "Your question here" --top-k 3
"""

import argparse
from retrieval import retrieve, format_citation


def main():
    parser = argparse.ArgumentParser(description="Query the document store.")
    parser.add_argument("question", help="Question to search for")
    parser.add_argument("--top-k", type=int, default=5, help="Number of results (default: 5)")
    args = parser.parse_args()

    print(f"\nQuery: {args.question}\n{'─' * 60}")
    chunks = retrieve(args.question, top_k=args.top_k)

    if not chunks:
        print("No results found. Have you run `python ingest.py` first?")
        return

    for i, chunk in enumerate(chunks, start=1):
        citation = format_citation(chunk)
        print(f"\n[{i}] {citation}  (distance: {chunk['distance']:.4f})")
        print(chunk["text"][:400].strip())
        if len(chunk["text"]) > 400:
            print("...")


if __name__ == "__main__":
    main()
