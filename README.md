# RAG + LLM Wiki System

A prototype that combines retrieval-augmented generation (RAG) with an LLM-generated wiki.

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...
```

## Workflow

### 1. Ingest documents

Place PDF, DOCX, TXT, or Markdown files in `data/documents/`, then:

```bash
python ingest.py
```

### 2. Test retrieval

```bash
python query.py "What is the main topic of these documents?"
python query.py "Explain X" --top-k 3
```

### 3. Generate a cited answer

```bash
python answer.py "What does the document say about X?"
python answer.py "Explain Y" --top-k 6
```

Answers cite sources inline as `[N]`. If chunks don't support the answer, the model says so.

### 4. Generate or update a wiki page

```bash
python wiki_writer.py "Machine Learning"
python wiki_writer.py "Neural Networks" --top-k 8
python wiki_writer.py "Transformers" --question "How do attention mechanisms work?"
```

Pages are saved as Markdown in `wiki/`. If the page already exists it is updated
rather than replaced, and an update log is appended at the bottom.

Each wiki page contains: title, summary, key points (cited), definitions, related topics,
sources, last-updated date, and an update log.

## Project Layout

```
data/documents/   ← input files (PDF, DOCX, TXT, Markdown)
wiki/             ← generated wiki pages (Markdown)
chroma_db/        ← persisted vector store (auto-created)
ingest.py         ← extract → chunk → embed → store
retrieval.py      ← query vector DB, return cited chunks
query.py          ← CLI test harness for retrieval
answer.py         ← retrieve + generate cited answer via Claude
wiki_writer.py    ← generate or update a wiki page for a topic
```

## Run the App

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` with three tabs:

| Tab | What it does |
|-----|--------------|
| **Ask Questions** | Enter a question → retrieve chunks → cited answer |
| **Generate Wiki Page** | Enter a topic → retrieve chunks → create/update `wiki/<topic>.md` |
| **Browse Wiki** | Browse saved wiki pages side-by-side with raw Markdown |
