"""
Retrieval module: query ChromaDB and return ranked chunks with citations.
"""

from pathlib import Path

import chromadb
from chromadb.utils import embedding_functions

# Must match the path used in ingest.py and server.py — store in persistent volume
CHROMA_DIR = Path("data/chroma_db")
COLLECTION_NAME = "documents"
DEFAULT_TOP_K = 5

# Embedding model — must match the model used in ingest.py.
# paraphrase-MiniLM-L3-v2 is ~3x faster than the default all-MiniLM-L6-v2
# with only a small accuracy trade-off, making retrieval near-instant.
EMBEDDING_MODEL = "paraphrase-MiniLM-L3-v2"

# Cached at module level so the model loads once per process, not once per query.
_ef = None


def get_embedding_function():
    global _ef
    if _ef is None:
        _ef = embedding_functions.SentenceTransformerEmbeddingFunction(
            model_name=EMBEDDING_MODEL
        )
    return _ef


def get_collection():
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(COLLECTION_NAME, embedding_function=get_embedding_function())


def retrieve(query: str, top_k: int = DEFAULT_TOP_K) -> list[dict]:
    """
    Query the vector DB and return a list of result dicts:
      {text, source, page, chunk_index, distance}
    """
    collection = get_collection()
    results = collection.query(query_texts=[query], n_results=top_k)

    chunks = []
    for i in range(len(results["documents"][0])):
        meta = results["metadatas"][0][i]
        chunks.append({
            "text": results["documents"][0][i],
            "source": meta.get("source", "unknown"),
            "page": meta.get("page", "N/A"),
            "chunk_index": meta.get("chunk_index", -1),
            "distance": results["distances"][0][i],
        })
    return chunks


def format_citation(chunk: dict) -> str:
    page = chunk["page"]
    if page and page != "N/A":
        return f"{chunk['source']} (page {page})"
    return chunk["source"]
