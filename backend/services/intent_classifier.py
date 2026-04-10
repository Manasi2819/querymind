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

FORBIDDEN_INTENT_KEYWORDS = [
    "delete", "drop", "truncate", "update", "insert", "alter", "create", "modify", "remove", "change", "set", "clear"
]

def classify_intent(question: str, has_db: bool, has_docs: bool, provider: str = None, api_key: str = None, model: str = None, history: str = "") -> str:
    """
    Returns: 'sql' | 'rag' | 'general'
    Uses LLM for smart routing if provider is given, falling back to keywords.
    """
    if provider:
        try:
            from services.llm_service import get_llm
            llm = get_llm(provider=provider, api_key=api_key, model=model)
            
            prompt = f"""You are an intent classifier for a database querying assistant.
You must classify the user's latest question into one of three categories:
1. 'sql' - The user is asking for data, metrics, counts, names, IDs, prices, numbers, or records that would typically be found in a structured SQL database. (e.g. "what is the name of the first user", "what is the rate", "how many contracts", "which route has the highest rate")
2. 'rag' - The user is asking about the definition, meaning, or documentation of technical/domain-specific terms. (e.g. "what is the meaning of X", "explain how the system works", "according to the document")
3. 'unauthorized' - The user is asking to modify, delete, insert, update, drop, or change any data or database structure. (e.g. "delete record X", "drop the table", "update price to 50", "change name to Y", "remove all logs")
4. 'general' - General greetings, small talk, coding questions, math, or general knowledge completely unrelated to the enterprise database/documents. (e.g. "what is 1+1", "who is the president", "what is llm", "what is python", "hello")

Context:
- Database configured: {has_db}
- Documents configured: {has_docs}
- Recent History:
{history}

Latest Question: "{question}"

Instructions:
- Return ONLY the exact classification text: 'sql', 'rag', or 'general'.
- Do NOT return any preamble, code blocks, or formatting."""
            
            response = llm.invoke(prompt)
            classification = response.content.strip().lower()
            
            # Extract just the classification keyword
            for valid_category in ['sql', 'rag', 'unauthorized', 'general']:
                if valid_category in classification:
                    # Sanity check against missing infrastructure
                    if valid_category == 'sql' and not has_db:
                        return 'rag' if has_docs else 'general'
                    if valid_category == 'rag' and not has_docs:
                        return 'sql' if has_db else 'general'
                    return valid_category
        except Exception as e:
            print(f"LLM Classification failed, falling back to keywords: {e}")
            pass

    # Keyword fallback
    q = question.lower()
    
    if has_db and any(kw in q for kw in FORBIDDEN_INTENT_KEYWORDS):
        return "unauthorized"

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
