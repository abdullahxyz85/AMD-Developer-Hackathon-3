"""
Shared fixtures for RAG tests.

Tests run from anywhere; all paths resolve relative to RAG/ (this file's parent).
"""

import json
import pickle
import sys
from pathlib import Path

import pytest

RAG_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAG_DIR / "scripts"))

from ingest import COLLECTION_NAME, tokenize  # noqa: E402

CHROMA_DIR = RAG_DIR / "knowledge" / "index" / "chroma"
BM25_PATH = RAG_DIR / "knowledge" / "index" / "bm25.pkl"
CHUNKS_PATH = RAG_DIR / "knowledge" / "index" / "chunks.json"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


@pytest.fixture(scope="session")
def chunk_store():
    """id -> chunk dict for all ingested chunks."""
    data = json.load(open(CHUNKS_PATH, encoding="utf-8"))
    return {c["id"]: c for c in data["chunks"]}


@pytest.fixture(scope="session")
def bm25_index():
    """The pickled BM25 index: {'ids': [...], 'bm25': BM25Okapi}."""
    return pickle.load(open(BM25_PATH, "rb"))


@pytest.fixture(scope="session")
def chroma_collection():
    import chromadb

    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_collection(COLLECTION_NAME)


@pytest.fixture(scope="session")
def embed_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBED_MODEL)


def dense_query(collection, embed_model, query, n=3, where=None):
    """Dense (vector) retrieval; returns [(chunk_id, cosine_distance), ...]."""
    emb = embed_model.encode([query], normalize_embeddings=True)[0].tolist()
    res = collection.query(query_embeddings=[emb], n_results=n, where=where)
    return list(zip(res["ids"][0], res["distances"][0]))


def bm25_query(index, query, n=3):
    """Keyword retrieval; returns [(chunk_id, score), ...] best first."""
    scores = index["bm25"].get_scores(tokenize(query))
    order = sorted(range(len(scores)), key=lambda i: -scores[i])[:n]
    return [(index["ids"][i], scores[i]) for i in order]
