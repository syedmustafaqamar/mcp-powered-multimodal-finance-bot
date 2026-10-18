from ai.agents.orchestrator import FinanceRouter


def test_finance_query_routes_to_database():
    assert FinanceRouter._fallback("What was Tesla revenue in Q2 2026?") == "database_agent"


def test_document_query_routes_to_documents():
    assert FinanceRouter._fallback("What changed in FSD v14 lite?") == "document_agent"


def test_hybrid_query_routes_to_hybrid():
    assert (
        FinanceRouter._fallback(
            "What was Tesla revenue and what AI software initiatives were highlighted?"
        )
        == "hybrid_agent"
    )


def test_general_query_routes_to_general():
    assert FinanceRouter._fallback("What is gross margin?") == "general_agent"
