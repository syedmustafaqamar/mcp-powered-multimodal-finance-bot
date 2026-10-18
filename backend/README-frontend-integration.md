# Frontend integration notes

The React app uses the existing API routes:

| Feature | Endpoint | Auth |
|---|---|---|
| Register | `POST /user/register` | No |
| Login | `POST /user/login` (OAuth2 form fields) | No |
| Current user | `GET /user/me` | Bearer token |
| API health | `GET /health` | No |
| Ask | `POST /ask` | Bearer token |
| Task polling | `GET /tasks/{task_id}` | Bearer token |
| Document ingestion | `POST /ingest_document` | Bearer token |

Set `CORS_ORIGINS` in `.env` to the exact frontend origins. `MAX_UPLOAD_MB` controls the backend upload limit. The frontend's `.env.example` configures `VITE_API_BASE_URL`.

The frontend polls asynchronous Celery tasks. A successful task is expected to return the worker's result under `result`, and an answer result can include `answer`, `agent`, `sources`, `database_rows`, and `tools_used`.

Before production, persist task ownership and verify the current user is allowed to read a task result; add a robust auth/session strategy, rate limits, and automated end-to-end tests.
