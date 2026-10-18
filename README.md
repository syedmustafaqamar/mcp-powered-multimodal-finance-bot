# FinSight — Finance Research Bot

A full-stack project with FastAPI finance research backend and a React + TypeScript frontend.

## Project layout

```text
finance-research-bot/
├── backend/       # Existing FastAPI, RAG, MCP, Celery worker and database code
├── frontend/      # React + TypeScript + Vite user interface
└── README.md
```

## Frontend features

- Login and registration using the existing `/user/login`, `/user/register`, and `/user/me` routes.
- Research chat wired to `POST /ask` and task polling via `GET /tasks/{task_id}`.
- Evidence panel for agent name, tools used, document sources, and structured database rows returned by the backend.
- PDF/image uploads to `/ingest_document`, with progress polling.
- Configurable number of retrieval sources, example prompts, recent questions, backend health status, responsive layout, loading states, and API error feedback.
- Typed API helper functions and shared TypeScript response types.

## Run locally

### 1. Start backend dependencies

Follow `backend/README.md` for the original project setup. In brief, the backend needs PostgreSQL, Redis, Ollama and the configured local models.

From the `backend/` directory:

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux: source .venv/bin/activate
pip install -r app/requirements.txt
pip install -r ai/requirements.txt
cp .env.example .env
```

Initialize the database if needed:

```bash
python scripts/init_db.py
```

Start the API from `backend/`:

```bash
uvicorn app.main:app --reload
```

In a separate terminal, from `backend/`, start the Celery worker:

```bash
celery -A ai.celery.cel_app:celery_app worker --queues=ai_queue --pool=solo --loglevel=info
```

`--pool=solo` is useful for a local Windows development setup. Ensure PostgreSQL, Redis and Ollama are already running.

### 2. Start the frontend

From `frontend/`:

```bash
npm install
cp .env.example .env
npm run dev
```

Open the Vite URL, usually `http://127.0.0.1:5173`. Set `VITE_API_BASE_URL` in `frontend/.env` if the API runs elsewhere.

The backend CORS setting defaults to the Vite localhost origins. If you change the frontend origin, update `CORS_ORIGINS` in `backend/.env`.

## Structure

- **Separation of concerns:** React components handle presentation and interaction; `api.ts` owns HTTP/auth/task-polling concerns; TypeScript types describe API payloads.
- **Asynchronous work:** the backend returns a Celery task ID rather than holding a request open while the model runs. The frontend polls task status and presents progress/errors.
- **Evidence-first UI:** the right panel exposes the sources, tools, and structured rows returned by the research workflow rather than showing only a generated answer.
- **Security considerations:** the UI uses a bearer token for authenticated routes and the backend now protects `/ask`, which previously lacked the active-user dependency. CORS origins and upload size are configurable.
- **Production improvements to discuss:** use secure HttpOnly cookies or a robust OAuth/OIDC flow instead of localStorage tokens; authorize each task against its owner; use SSE/WebSockets or a managed job event channel instead of polling; add rate limits, file-content validation, observability, and automated integration tests.

## Important notes

- This is a development/portfolio UI, not a production security review.
- Frontend upload validation is a usability feature; the backend enforces the configured size limit and file extension allowlist.
- The UI expects the backend task result to contain an `answer` field and optional `agent`, `sources`, `database_rows`, and `tools_used` fields. If the worker response schema changes, update `frontend/src/types.ts` and the evidence panel accordingly.
- AI-generated finance answers may be incomplete or incorrect; validate important conclusions against source material.
