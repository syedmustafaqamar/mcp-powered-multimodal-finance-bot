from ai.config import settings
from .ollama import OllamaClient
from .vector_store import VectorStore


class RAGService:
    def __init__(self):
        self.ollama = OllamaClient()
        self.vector_store = VectorStore()

    def search(self, query: str, top_k: int | None = None) -> list[dict]:
        top_k = top_k or settings.RETRIEVAL_TOP_K
        embeddings = self.ollama.embed([query])
        return self.vector_store.query(embeddings[0], top_k)

    def answer(self, query: str, top_k: int | None = None) -> dict:
        results = self.search(query, top_k)
        if not results:
            return {"answer": "I could not find relevant information in the indexed documents.", "sources": []}

        context_parts = []
        sources = []
        for result in results:
            metadata = result["metadata"]
            source = metadata.get("source", "unknown")
            page = metadata.get("page_number", 0)
            context_parts.append(f"[{source}, page {page}]\n{result['content']}")
            sources.append({
                "source": source,
                "page_number": page,
                "type": metadata.get("type", "text"),
                "distance": result["distance"],
            })

        answer = self.ollama.chat(query, "\n\n---\n\n".join(context_parts))
        return {"answer": answer, "sources": sources}
