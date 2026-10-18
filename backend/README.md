# Finance Multimodal RAG + MCP

A local, portfolio-ready prototype of a **finance research bot** built with:

- FastAPI
- PostgreSQL
- Redis + Celery
- Ollama (vision, LLM, embeddings)
- ChromaDB
- Model Context Protocol (MCP)
- A small multi-agent workflow

There are **no paid APIs and no API keys required**. Ollama runs the models locally, PostgreSQL is local, and the MCP server is local.

## What was added

The original project already had:

`document -> multimodal extraction -> normalization -> chunking -> embeddings -> Chroma -> RAG`

This version adds:

`question -> MCP capability discovery -> LLM router -> specialist agent -> MCP tool -> evidence -> answer`

### Agents

| Agent | When it is selected | MCP tool |
|---|---|---|
| `document_agent` | Report/document questions | `search_financial_documents` |
| `database_agent` | Structured financial numbers and periods | `search_financial_database` |
| `hybrid_agent` | Questions requiring both narrative + numbers | both tools |
| `general_agent` | General finance concepts | no retrieval tool |

The router first asks MCP what tools are available, then asks the local Ollama model to select the most appropriate specialist.

## Tesla finance use case

`shared/documents/Tesla.pdf` is the multimodal source document. It contains Tesla AI/software material such as FSD v14 lite, AI3/AI4, AI inference compute, the Summer Release, Grok functionality, and Automatic Navigation.

The PostgreSQL demo dataset contains selected **Tesla Q2 2026 financial and operating metrics** from Tesla's Q2 2026 Update, including:

- total revenue
- automotive revenue
- energy revenue
- services and other revenue
- gross profit / gross margin
- operating income / margin
- GAAP net income
- diluted GAAP EPS
- operating cash flow
- capital expenditure
- free cash flow
- cash and investments
- vehicle deliveries
- active FSD subscriptions
- storage deployed

This gives the bot a useful hybrid finance scenario.

### Good demo questions

**Document agent**
- "What improvements were introduced in FSD v14 lite?"
- "What new capabilities were included in Tesla's Summer Release?"
- "What is Tesla doing with AI inference compute?"

**Database agent**
- "What was Tesla's Q2 2026 revenue?"
- "What was Tesla's Q2 2026 operating margin?"
- "How much free cash flow did Tesla generate in Q2 2026?"
- "How many active FSD subscriptions did Tesla have in Q2 2026?"

**Hybrid agent**
- "Tesla's Q2 2026 revenue grew strongly, but what AI/software initiatives were highlighted alongside the financial results?"
- "How do Tesla's FSD subscriptions relate to the company's Q2 2026 business performance?"

## Architecture

```text
                         +------------------+
                         |     FastAPI      |
                         +--------+---------+
                                  |
                                  | Celery task
                                  v
                         +------------------+
                         |   AI Worker      |
                         +--------+---------+
                                  |
                         +--------v---------+
                         | Finance          |
                         | Orchestrator     |
                         +--------+---------+
                                  |
                         1. list MCP tools
                                  |
                         2. local LLM router
                                  |
                +-----------------+-----------------+
                |                 |                 |
                v                 v                 v
        Document Agent     Database Agent     Hybrid Agent
                |                 |                 |
                +-----------------+-----------------+
                                  |
                              MCP Client
                                  |
                         +--------v---------+
                         |   MCP Server     |
                         | read-only tools  |
                         +---+----------+---+
                             |          |
                        ChromaDB   PostgreSQL
                             |
                         Ollama embeddings
                             |
                         Ollama generation

Ingestion remains:

PDF/image -> PyMuPDF -> Ollama Vision -> normalized elements
-> structure-aware chunks -> Ollama embeddings -> ChromaDB
```

## MCP design

The MCP server is in:

`ai/mcp/server.py`

It exposes four read-only tools:

1. `search_financial_documents`
2. `search_financial_database`
3. `database_schema`
4. `execute_readonly_sql`

The application uses the official MCP Python SDK and an **in-process MCP client**, so the multi-agent workflow does not need another network service just to talk to its own tools.

The MCP server can also be started independently using Streamable HTTP. This makes it easy to inspect with an MCP-compatible client/Inspector.

## PostgreSQL

The database URL is intentionally **not hard-coded** and does not need to be placed in `.env`.

It is built from:

```text
DATABASE_NAME
DATABASE_USER
DATABASE_PASSWORD
DATABASE_HOST
DATABASE_PORT
```

For example:

```text
postgresql+psycopg://postgres:toor@localhost:5432/localdb
```

Both the FastAPI application and AI worker use the same database settings.

## Setup

### 1. Create the virtual environment

```powershell
python -m venv .venv
.venv\Scripts\activate
```

Install both dependency sets:

```powershell
pip install -r app/requirements.txt
pip install -r ai/requirements.txt
```

### 2. Configure environment

```powershell
copy .env.example .env
```

Update PostgreSQL credentials if needed.

### 3. Start PostgreSQL

Make sure PostgreSQL is running and the database named in `DATABASE_NAME` exists.

For the default configuration:

```text
database: localdb
user: postgres
password: toor
host: localhost
port: 5432
```

### 4. Initialize the database

From the project root:

```powershell
python scripts/init_db.py
```

This creates:

- `users`
- `financial_metrics`

and loads the demo Tesla Q2 2026 metrics.

### 5. Start Ollama

Install Ollama, then:

```powershell
ollama pull llava:7b-v1.6
ollama pull nomic-embed-text
ollama pull qwen2.5:7b
```

If the machine is memory constrained, change `OLLAMA_LLM_MODEL` in `.env` to another installed model.

### 6. Start Redis

For a local Windows setup, Redis can run in WSL2.

```bash
sudo service redis-server start
redis-cli ping
```

If Redis is bound to a WSL address, put that address into the Redis URLs in `.env`.

### 7. Start FastAPI

```powershell
uvicorn app.main:app --reload
```

### 8. Start the AI worker

On Windows use Celery's solo pool:

```powershell
celery -A ai.celery.cel_app:celery_app worker --queues=ai_queue --pool=solo --loglevel=info
```

### 9. Optional: start the standalone MCP server

```powershell
python -m ai.mcp.server
```

It will expose MCP over Streamable HTTP at:

```text
http://127.0.0.1:8001/mcp
```

The multi-agent workflow does not require this separate process because it uses the same MCP server in-process.

## API flow

### Register

`POST /user/register`

```json
{
  "username": "mustafa",
  "email": "mustafa@example.com",
  "password": "password123"
}
```

### Login

`POST /user/login`

Use OAuth2 form fields:

```text
username=mustafa
password=password123
```

Copy the returned bearer token into Swagger's **Authorize** button.

### Ingest Tesla PDF

`POST /ingest_document`

Upload:

```text
shared/documents/Tesla.pdf
```

Then poll:

`GET /tasks/{task_id}`

### Ask the finance bot

`POST /ask`

```json
{
  "query": "What was Tesla's Q2 2026 operating margin and what AI/software initiatives were highlighted?",
  "top_k": 5
}
```

The response task eventually contains:

```json
{
  "query": "...",
  "answer": "...",
  "agent": "hybrid_agent",
  "sources": [...],
  "database_rows": [...],
  "tools_used": [
    "search_financial_documents",
    "search_financial_database"
  ]
}
```

That `agent` and `tools_used` information is intentionally exposed so the prototype demonstrates the agentic/MCP decision path instead of hiding it.

## Why MCP is useful here

MCP is not being used as another vector database or as a replacement for RAG.

Instead, MCP provides a **standard tool boundary**:

```text
Agent
  |
  +--> document search
  |
  +--> structured finance database
  |
  +--> read-only SQL
  |
  +--> future finance tools
```

That means a future version can add tools such as:

- market-data provider
- portfolio database
- SEC filing search
- earnings calendar
- financial calculator
- risk analysis service

without rewriting the agent architecture.

For this prototype, everything remains local and keyless.

## Safety of the database tool

`execute_readonly_sql`:

- only accepts `SELECT`
- blocks write/DDL operations
- only allows the `financial_metrics` and `users` tables
- limits returned rows

The normal finance workflow does **not** need raw SQL; it uses the safer `search_financial_database` tool.

## Project structure

```text
ai/
  agents/
    orchestrator.py
  celery/
    tasks/
      ingestion.py
      rag.py
  ingestion/
    multimodal.py
  mcp/
    server.py
  services/
    ollama.py
    rag.py
    vector_store.py

app/
  auth/
  core/
    database.py
    config.py
  finance/
    models.py
  routes/
  main.py

scripts/
  init_db.py

shared/
  documents/
    Tesla.pdf
  chroma/
```

## Source for demo financial data

The seeded Q2 2026 metrics are based on Tesla's Q2 2026 Update / SEC filing, published July 2026. They are included as a clearly identified demo dataset so the MCP database agent has real structured financial data to query.

For a production system, replace the seed script with an ingestion process for your approved financial data source.

## Notes

- No OpenAI, Anthropic, Gemini, or other paid API is required.
- Ollama must be running locally.
- PostgreSQL must be running for the database agent.
- Redis must be running for Celery.
- ChromaDB remains local, matching the original learning/portfolio architecture.
- The MCP server uses the official Python SDK's current v2 API and Streamable HTTP transport.
