import re
from pathlib import Path
from uuid import uuid4

from celery.result import AsyncResult
from fastapi import Depends, FastAPI, File, HTTPException, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.auth.dependencies import get_current_active_user
from app.auth.models import User
from app.core.celery.cel_app import celery_app
from app.core.config import settings
from app.routes.v1.user import router as auth_router

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="2.0.0",
    description="Multimodal RAG with an MCP-aware multi-agent finance workflow.",
)

app.include_router(auth_router)


class AskRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


class SearchRequest(BaseModel):
    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


def _safe_filename(filename: str) -> str:
    name = Path(filename or "document").name
    name = re.sub(r"[^A-Za-z0-9._-]", "_", name)
    return name or "document"


def _enqueue(task_name: str, args: list):
    return celery_app.send_task(
        task_name,
        args=args,
        queue="ai_queue",
    )


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.post("/ingest_document", status_code=status.HTTP_202_ACCEPTED)
async def ingest_document(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
):
    filename = _safe_filename(file.filename or "document")
    document_id = str(uuid4())
    stored_name = f"{document_id}_{filename}"
    file_path = settings.DOCUMENTS_DIR / stored_name

    contents = await file.read()
    if not contents:
        raise HTTPException(status_code=400, detail="Uploaded file is empty")

    allowed = {
        ".pdf",
        ".png",
        ".jpg",
        ".jpeg",
        ".webp",
        ".bmp",
        ".tif",
        ".tiff",
    }
    if Path(filename).suffix.lower() not in allowed:
        raise HTTPException(status_code=400, detail="Unsupported file type")

    file_path.write_bytes(contents)

    task = _enqueue(
        "process_ingestion",
        [str(file_path), document_id, filename],
    )

    return JSONResponse(
        content={
            "task_id": task.id,
            "document_id": document_id,
            "filename": filename,
            "status": "queued",
        }
    )


@app.get("/tasks/{task_id}")
async def get_task_status(
    task_id: str,
    current_user: User = Depends(get_current_active_user),
):
    result = AsyncResult(task_id, app=celery_app)
    response = {
        "task_id": task_id,
        "status": result.status,
    }
    if result.successful():
        response["result"] = result.result
    elif result.failed():
        response["error"] = str(result.result)
    return response


@app.post("/search", status_code=status.HTTP_202_ACCEPTED)
async def search_documents(
    request: SearchRequest,
    current_user: User = Depends(get_current_active_user),
):
    task = _enqueue("ai.rag.search", [request.query, request.top_k])
    return {"task_id": task.id, "status": "queued"}


@app.post("/ask", status_code=status.HTTP_202_ACCEPTED)
async def ask_question(
    request: AskRequest,
):
    task = _enqueue("ai.rag.answer", [request.query, request.top_k])
    return {
        "task_id": task.id,
        "status": "queued",
        "workflow": "mcp_multi_agent",
    }
