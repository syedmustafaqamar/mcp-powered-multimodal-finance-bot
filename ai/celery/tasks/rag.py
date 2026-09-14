from ai.agents.orchestrator import FinanceOrchestrator
from ai.celery.cel_app import celery_app


@celery_app.task(name="ai.rag.search", queue="ai_queue")
def search_documents(query: str, top_k: int = 5):
    from ai.services.rag import RAGService

    service = RAGService()
    return {
        "query": query,
        "results": service.search(query, top_k),
    }


@celery_app.task(name="ai.rag.answer", queue="ai_queue")
def answer_question(query: str, top_k: int = 5):
    """Run the MCP-aware multi-agent finance workflow."""
    orchestrator = FinanceOrchestrator()
    return orchestrator.answer(query, top_k)
