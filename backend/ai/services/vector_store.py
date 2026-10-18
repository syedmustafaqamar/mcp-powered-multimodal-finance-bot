from typing import Any

import chromadb

from ai.config import settings


class VectorStore:
    """ChromaDB adapter. Keeps vector-database details out of ingestion/RAG logic."""

    def __init__(self):
        self.client = chromadb.PersistentClient(path=str(settings.CHROMA_DIR))
        self.collection = self.client.get_or_create_collection(
            name=settings.CHROMA_COLLECTION,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, chunks: list[dict[str, Any]], embeddings: list[list[float]]) -> None:
        if not chunks:
            return
        self.collection.upsert(
            ids=[chunk["id"] for chunk in chunks],
            embeddings=embeddings,
            documents=[chunk["content"] for chunk in chunks],
            metadatas=[
                {
                    "source": chunk["source"],
                    "document_id": chunk.get("document_id", ""),
                    "page_number": chunk["page_number"] or 0,
                    "type": chunk["type"],
                    "heading": chunk.get("heading") or "",
                }
                for chunk in chunks
            ],
        )

    def query(self, embedding: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        result = self.collection.query(
            query_embeddings=[embedding],
            n_results=top_k,
            include=["documents", "metadatas", "distances"],
        )
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]
        items = []
        for index, document in enumerate(documents):
            items.append({
                "content": document,
                "metadata": metadatas[index],
                "distance": distances[index],
            })
        return items

    def count(self) -> int:
        return self.collection.count()

    def delete_document(self, document_id: str) -> None:
        self.collection.delete(where={"document_id": document_id})
