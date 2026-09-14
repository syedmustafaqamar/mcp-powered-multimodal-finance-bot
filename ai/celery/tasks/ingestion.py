import logging
from pathlib import Path

from ai.celery.cel_app import celery_app
from ai.ingestion.multimodal import MultiModalIngestion
from ai.services.ollama import OllamaClient
from ai.services.vector_store import VectorStore

logger = logging.getLogger(__name__)


@celery_app.task(
    name="process_ingestion",
    queue="ai_queue",
)
def process_document(file_path: str, document_id: str, source_name: str):
    """Run the complete document ingestion pipeline."""
    path = Path(file_path)
    if not path.exists():
        raise FileNotFoundError(f"Document not found: {file_path}")

    logger.info("Starting ingestion: %s", path)

    ingestion = MultiModalIngestion(
        str(path),
        document_id=document_id,
        source_name=source_name,
    )
    pages = ingestion.extract_images()
    raw_elements = ingestion.extract_elements()
    elements = ingestion.normalize_elements()
    chunks = ingestion.create_chunks()

    if not chunks:
        return {
            "status": "completed",
            "file_path": str(path),
            "pages": len(pages),
            "elements": len(elements),
            "chunks": 0,
            "vectors": 0,
        }

    ollama = OllamaClient()
    vector_store = VectorStore()

    # Re-ingesting a document replaces its old vectors instead of duplicating them.
    vector_store.delete_document(document_id)

    batch_size = 16
    vector_count = 0
    for start in range(0, len(chunks), batch_size):
        batch = chunks[start:start + batch_size]
        embeddings = ollama.embed([chunk["content"] for chunk in batch])
        vector_store.upsert(batch, embeddings)
        vector_count += len(batch)

    logger.info(
        "Completed ingestion: %s pages=%s elements=%s chunks=%s vectors=%s",
        path.name,
        len(pages),
        len(elements),
        len(chunks),
        vector_count,
    )

    return {
        "status": "completed",
        "file_path": str(path),
        "document": source_name,
        "document_id": document_id,
        "pages": len(pages),
        "elements": len(elements),
        "raw_elements": len(raw_elements),
        "chunks": len(chunks),
        "vectors": vector_count,
    }
