"""
Memory: ChromaDB local with nomic-embed-text via Ollama.
Stores conversation turns, retrieves top-5 relevant history.
"""
from __future__ import annotations

import os
from typing import Optional

import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

DB_DIR = os.path.join(os.getcwd(), "vectorstore")
EMBED_MODEL = "nomic-embed-text"
OLLAMA_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
COLLECTION_NAME = "blinsky-memory"


class Memory:
    """Local ChromaDB conversation memory."""

    def __init__(self, db_dir: str = DB_DIR) -> None:
        os.makedirs(db_dir, exist_ok=True)
        emb_fn = OllamaEmbeddingFunction(
            model_name=EMBED_MODEL, url=OLLAMA_URL
        )
        self.client = chromadb.PersistentClient(path=db_dir)
        self.collection = self.client.get_or_create_collection(
            COLLECTION_NAME, embedding_function=emb_fn
        )

    def add(self, turn_id: str, user_text: str, bot_text: str) -> None:
        self.collection.add(
            documents=[user_text],
            metadatas=[{"bot_text": bot_text}],
            ids=[str(turn_id)],
        )

    def search(self, query: str, n_results: int = 5) -> list[dict]:
        res = self.collection.query(query_texts=[query], n_results=n_results)
        docs = res.get("documents", [[]])
        metas = res.get("metadatas", [[]])
        dists = res.get("distances", [[]])
        out = []
        for d, m, dist in zip(docs[0], metas[0], dists[0]):
            out.append(
                {
                    "user": d,
                    "assistant": m.get("bot_text", ""),
                    "score": float(dist),
                }
            )
        return out
