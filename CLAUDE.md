# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

RAG + LLM Wiki System — a prototype that combines retrieval-augmented generation (RAG) with an LLM-generated wiki. RAG retrieves information; the LLM wiki organizes it.

## Stack

- **Frontend**: Streamlit
- **Backend**: FastAPI (if needed)
- **Vector DB**: ChromaDB or FAISS
- **Language**: Python
- **Wiki storage**: Markdown files in `wiki/`
- **Document input**: `data/documents/` (PDF, DOCX, TXT, Markdown)

## Directory Layout

```
data/documents/   # Input documents (use sample/public data only during dev)
wiki/             # LLM-generated wiki pages (Markdown)
```

## Pipeline

1. Extract text from documents in `data/documents/`
2. Chunk extracted text
3. Embed chunks and store in vector DB (ChromaDB or FAISS)
4. On query: retrieve relevant chunks
5. Generate answer with citations (document name + page number where available)
6. Generate or update a wiki page in `wiki/`

## Citations & Safety

- Every answer must cite source documents (name + page if available)
- Mark uncertain or unsupported claims explicitly
- Do not ingest confidential data without approval
- Wiki pages require human review before official use

## Style

Prefer clear, readable code over abstractions. Avoid over-engineering for a prototype.
