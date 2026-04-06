"""
Intent classifier — decides if a question needs SQL, RAG, or general LLM response.
Simple keyword + LLM-based routing (no separate model call needed for phi3-mini).
"""

SQL_KEYWORDS = [
    "how many", "count", "total", "average", "avg", "sum", "list all",
    "show me", "select", "query", "table", "rows", "records", "filter",
    "group by", "where", "find all", "top", "bottom", "highest", "lowest",
]

DOC_KEYWORDS = [
    "what does", "explain", "definition", "according to", "document says",
    "data dictionary", "field", "column description", "what is the meaning",
    "describe", "what is", "how is defined",
]

def classify_intent(question: str, has_db: bool, has_docs: bool) -> str:
    """
    Returns: 'sql' | 'rag' | 'general'
    """
    q = question.lower()

    if has_db and any(kw in q for kw in SQL_KEYWORDS):
        return "sql"

    if has_docs and any(kw in q for kw in DOC_KEYWORDS):
        return "rag"

    # Fallback: if DB configured, try SQL; else RAG; else general
    if has_db:
        return "sql"
    if has_docs:
        return "rag"
    return "general"
