"""MCP tools for the finance RAG prototype.

The same MCP server is used in-process by the agent workflow and can also be
run as a standalone Streamable HTTP server for MCP Inspector/other hosts.
"""

import re
from typing import Any

from mcp.server import MCPServer
from sqlalchemy import create_engine, text

from ai.config import settings
from ai.services.rag import RAGService

mcp = MCPServer(
    "finance-rag-tools",
    instructions=(
        "Read-only finance research tools. Use document search for facts from "
        "indexed reports and database search for structured financial metrics."
    ),
)

rag_service = RAGService()
db_engine = create_engine(settings.DATABASE_URL, pool_pre_ping=True)

_BLOCKED_SQL = re.compile(
    r"\b(insert|update|delete|drop|alter|truncate|create|grant|revoke|copy|call|execute)\b",
    re.IGNORECASE,
)
_ALLOWED_SQL = re.compile(
    r"\b(from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)",
    re.IGNORECASE,
)
_ALLOWED_TABLES = {"financial_metrics", "users"}


@mcp.tool()
def search_financial_documents(query: str, top_k: int = 5) -> dict[str, Any]:
    """Search indexed financial/company documents and return relevant passages with sources."""
    results = rag_service.search(query, top_k)
    return {
        "query": query,
        "results": results,
    }


@mcp.tool()
def search_financial_database(query: str, limit: int = 10) -> dict[str, Any]:
    """Search structured financial_metrics records using a natural-language keyword query."""
    limit = max(1, min(limit, 25))
    words = [
        word.lower()
        for word in re.findall(r"[A-Za-z0-9.]+", query)
        if len(word) > 1
    ]

    if not words:
        return {"query": query, "rows": []}

    conditions = []
    params: dict[str, Any] = {"limit": limit}

    for index, word in enumerate(words[:12]):
        key = f"term_{index}"
        conditions.append(
            "lower(concat_ws(' ', company, period, metric, unit, source)) LIKE :"
            + key
        )
        params[key] = f"%{word}%"

    statement = text(
        """
        SELECT company, period, metric, value, unit, source
        FROM financial_metrics
        WHERE
            """
        + " OR ".join(conditions)
        + """
        ORDER BY company, period, metric
        LIMIT :limit
        """
    )

    try:
        with db_engine.connect() as connection:
            rows = connection.execute(statement, params).mappings().all()
    except Exception as exc:
        return {
            "query": query,
            "rows": [],
            "error": (
                "Database query failed. Run `python scripts/init_db.py` first "
                "and verify PostgreSQL settings."
            ),
            "detail": str(exc),
        }

    return {"query": query, "rows": [dict(row) for row in rows]}


@mcp.tool()
def database_schema() -> dict[str, Any]:
    """Return the small read-only database schema relevant to the finance agent."""
    return {
        "tables": {
            "financial_metrics": [
                "company",
                "period",
                "metric",
                "value",
                "unit",
                "source",
            ],
            "users": ["id", "username", "email", "role", "is_active", "created_at"],
        }
    }


@mcp.tool()
def execute_readonly_sql(sql: str) -> dict[str, Any]:
    """Execute a read-only SELECT against allow-listed tables for analyst-style exploration."""
    normalized = sql.strip().rstrip(";").strip()

    if not normalized.lower().startswith("select"):
        return {"error": "Only SELECT statements are allowed."}

    if _BLOCKED_SQL.search(normalized):
        return {"error": "Statement contains a blocked SQL operation."}

    tables = {match.group(2).lower() for match in _ALLOWED_SQL.finditer(normalized)}
    if not tables or not tables.issubset(_ALLOWED_TABLES):
        return {
            "error": (
                "Only these tables are available to the read-only MCP SQL tool: "
                + ", ".join(sorted(_ALLOWED_TABLES))
            )
        }

    try:
        with db_engine.connect() as connection:
            result = connection.execute(text(normalized))
            rows = result.mappings().fetchmany(25)
    except Exception as exc:
        return {"error": f"Read-only SQL failed: {exc}"}

    return {"rows": [dict(row) for row in rows], "row_count": len(rows)}


def run_server() -> None:
    mcp.run(
        transport="streamable-http",
        host=settings.MCP_HOST,
        port=settings.MCP_PORT,
        streamable_http_path="/mcp",
        json_response=True,
        stateless_http=True,
    )


if __name__ == "__main__":
    run_server()
