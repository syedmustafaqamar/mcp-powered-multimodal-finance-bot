import asyncio
import json
import logging
import re
from dataclasses import dataclass
from typing import Any, Callable

from mcp import Client

from ai.config import settings
from ai.mcp.server import mcp
from ai.services.ollama import OllamaClient

logger = logging.getLogger(__name__)


@dataclass
class AgentResult:
    agent: str
    answer: str
    sources: list[dict[str, Any]]
    database_rows: list[dict[str, Any]]
    tools_used: list[str]


class FinanceRouter:
    """LLM router that chooses a specialist using the capabilities exposed by MCP."""

    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    def choose(self, query: str, tool_descriptions: str) -> str:
        prompt = f"""
You are the routing brain of a finance research assistant.

Available MCP tools:
{tool_descriptions}

Choose exactly ONE specialist:
- document_agent: facts, explanations, product/software/AI details, or anything that should be grounded in indexed reports.
- database_agent: structured financial metrics, numbers, periods, comparisons, or calculations from the finance database.
- hybrid_agent: a question that clearly needs BOTH document evidence and structured financial data.
- general_agent: general finance concepts that do not require company-specific data.

Return ONLY JSON:
{{"agent": "document_agent|database_agent|hybrid_agent|general_agent", "reason": "short reason"}}

User query:
{query}
"""
        try:
            raw = self.ollama.chat_raw(
                messages=[
                    {
                        "role": "system",
                        "content": "Route finance questions conservatively. Never invent data.",
                    },
                    {"role": "user", "content": prompt},
                ],
                format="json",
            )
            payload = json.loads(raw)
            agent = payload.get("agent", "")
            if agent in {
                "document_agent",
                "database_agent",
                "hybrid_agent",
                "general_agent",
            }:
                return agent
        except Exception as e:
            logger.exception("LLM router failed; falling back to deterministic routing")

        return self._fallback(query)

    @staticmethod
    def _fallback(query: str) -> str:
        lowered = query.lower()
        finance_terms = {
            "revenue",
            "income",
            "profit",
            "margin",
            "eps",
            "cash",
            "ebitda",
            "capex",
            "financial",
            "quarter",
            "q1",
            "q2",
            "q3",
            "q4",
        }
        document_terms = {
            "fsd",
            "grok",
            "software",
            "ai",
            "robotaxi",
            "cybercab",
            "optimus",
            "model y",
            "feature",
        }

        has_finance = any(term in lowered for term in finance_terms)
        has_document = any(term in lowered for term in document_terms)
        has_specific_data_request = (
            "tesla" in lowered
            or any(term in lowered for term in {"q1", "q2", "q3", "q4", "2025", "2026"})
            or any(
                phrase in lowered
                for phrase in {"how much", "what was", "what were", "compare"}
            )
        )

        if has_finance and has_document:
            return "hybrid_agent"
        if has_finance and has_specific_data_request:
            return "database_agent"
        if has_document:
            return "document_agent"
        return "general_agent"


class BaseFinanceAgent:
    def __init__(self, ollama: OllamaClient):
        self.ollama = ollama

    async def call_tool(self, client: Client, name: str, arguments: dict[str, Any]) -> Any:
        result = await client.call_tool(name, arguments)
        if result.is_error:
            raise RuntimeError(f"MCP tool {name!r} returned an error")
        return result.structured_content


class DocumentAgent(BaseFinanceAgent):
    async def run(self, client: Client, query: str, top_k: int) -> AgentResult:
        data = await self.call_tool(
            client,
            "search_financial_documents",
            {"query": query, "top_k": top_k},
        )
        results = data.get("results", [])
        answer = self._answer_from_results(query, results)

        sources = []
        for result in results:
            metadata = result.get("metadata", {})
            sources.append(
                {
                    "source": metadata.get("source", "unknown"),
                    "page_number": metadata.get("page_number", 0),
                    "type": metadata.get("type", "text"),
                    "distance": result.get("distance"),
                }
            )

        return AgentResult(
            agent="document_agent",
            answer=answer,
            sources=sources,
            database_rows=[],
            tools_used=["search_financial_documents"],
        )

    def _answer_from_results(self, query: str, results: list[dict[str, Any]]) -> str:
        if not results:
            return "I could not find relevant information in the indexed documents."

        context = []
        for result in results:
            metadata = result.get("metadata", {})
            context.append(
                f"[{metadata.get('source', 'unknown')}, page {metadata.get('page_number', 0)}]\n"
                f"{result.get('content', '')}"
            )

        return self.ollama.chat(query, "\n\n---\n\n".join(context))


class DatabaseAgent(BaseFinanceAgent):
    async def run(self, client: Client, query: str, top_k: int) -> AgentResult:
        data = await self.call_tool(
            client,
            "search_financial_database",
            {"query": query, "limit": max(top_k, 10)},
        )
        rows = data.get("rows", [])
        if not rows:
            return AgentResult(
                agent="database_agent",
                answer="I could not find matching structured financial data in the database.",
                sources=[],
                database_rows=[],
                tools_used=["search_financial_database"],
            )

        context = json.dumps(rows, indent=2, default=str)
        answer = self.ollama.chat(
            query,
            "Structured financial database results:\n" + context,
        )
        return AgentResult(
            agent="database_agent",
            answer=answer,
            sources=[
                {
                    "source": row.get("source", "financial_metrics"),
                    "period": row.get("period"),
                    "metric": row.get("metric"),
                }
                for row in rows
            ],
            database_rows=rows,
            tools_used=["search_financial_database"],
        )


class HybridAgent(BaseFinanceAgent):
    async def run(self, client: Client, query: str, top_k: int) -> AgentResult:
        document_data = await self.call_tool(
            client,
            "search_financial_documents",
            {"query": query, "top_k": top_k},
        )
        database_data = await self.call_tool(
            client,
            "search_financial_database",
            {"query": query, "limit": max(top_k, 10)},
        )

        document_results = document_data.get("results", [])
        database_rows = database_data.get("rows", [])

        context_parts = []
        for result in document_results:
            metadata = result.get("metadata", {})
            context_parts.append(
                f"DOCUMENT [{metadata.get('source', 'unknown')}, "
                f"page {metadata.get('page_number', 0)}]\n{result.get('content', '')}"
            )

        if database_rows:
            context_parts.append(
                "DATABASE RESULTS\n" + json.dumps(database_rows, indent=2, default=str)
            )

        if not context_parts:
            answer = "I could not find relevant information in either the indexed documents or finance database."
        else:
            answer = self.ollama.chat(
                query,
                "\n\n---\n\n".join(context_parts),
            )

        sources = []
        for result in document_results:
            metadata = result.get("metadata", {})
            sources.append(
                {
                    "source": metadata.get("source", "unknown"),
                    "page_number": metadata.get("page_number", 0),
                    "type": metadata.get("type", "text"),
                    "distance": result.get("distance"),
                }
            )

        return AgentResult(
            agent="hybrid_agent",
            answer=answer,
            sources=sources,
            database_rows=database_rows,
            tools_used=[
                "search_financial_documents",
                "search_financial_database",
            ],
        )


class GeneralAgent(BaseFinanceAgent):
    async def run(self, client: Client, query: str, top_k: int) -> AgentResult:
        answer = self.ollama.chat(
            query,
            (
                "You are a general finance education assistant. "
                "Explain concepts clearly. Do not present unverified company-specific "
                "or current market facts as facts."
            ),
        )
        return AgentResult(
            agent="general_agent",
            answer=answer,
            sources=[],
            database_rows=[],
            tools_used=[],
        )


class FinanceOrchestrator:
    """MCP-aware multi-agent workflow.

    1. Discover MCP capabilities.
    2. Ask a local Ollama router to choose a specialist.
    3. Run that specialist through MCP tools.
    """

    def __init__(self):
        self.ollama = OllamaClient()
        self.router = FinanceRouter(self.ollama)
        self.agents: dict[str, Callable[..., Any]] = {
            "document_agent": DocumentAgent(self.ollama),
            "database_agent": DatabaseAgent(self.ollama),
            "hybrid_agent": HybridAgent(self.ollama),
            "general_agent": GeneralAgent(self.ollama),
        }

    async def answer_async(self, query: str, top_k: int = 5) -> dict[str, Any]:
        async with Client(mcp) as client:
            tools = await client.list_tools()
            tool_descriptions = "\n".join(
                f"- {tool.name}: {tool.description or ''}" for tool in tools.tools
            )

            agent_name = self.router.choose(query, tool_descriptions)
            agent = self.agents[agent_name]
            result = await agent.run(client, query, top_k)

            return {
                "query": query,
                "answer": result.answer,
                "agent": result.agent,
                "sources": result.sources,
                "database_rows": result.database_rows,
                "tools_used": result.tools_used,
            }

    def answer(self, query: str, top_k: int = 5) -> dict[str, Any]:
        return asyncio.run(self.answer_async(query, top_k))
