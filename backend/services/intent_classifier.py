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
    Returns: 'sql_with_context' | 'rag' | 'chat' | 'unauthorized'
    Uses LLM for smart routing if provider is given, falling back to keywords.
    """
    if provider:
        try:
            from services.llm_service import get_llm
            llm = get_llm(provider=provider, api_key=api_key, model=model)
            
            prompt = f"""You are an intent classifier for an enterprise database assistant.
You must classify the user's latest question into one of four categories:

1. 'sql_with_context' - The user is asking for data, metrics, counts, names, IDs, prices, numbers, or records that would typically be found in a structured SQL database. This includes questions where external knowledge (from JSON/CSV/SQL files) might help construct a better query. (e.g. "what is the name of the first user", "how many contracts", "show me sales for electronics products")
2. 'rag' - The user is asking only about the definition, meaning, or documentation of technical/domain-specific terms from the uploaded files, WITHOUT needing database access. (e.g. "what is the meaning of X", "explain how the system works", "according to the document")
3. 'unauthorized' - The user is asking to modify, delete, insert, update, drop, or change any data or database structure. (e.g. "delete record X", "drop the table", "update price to 50")
4. 'chat' - General greetings, small talk, general knowledge, math, coding, or ANY question completely unrelated to the specific enterprise database or documentation. If the question doesn't require looking up data or documents, it is 'chat'. (e.g. "hello", "who is the president", "how are you", "what is 1+1")

Context:
- Database configured: {has_db}
- Documents configured: {has_docs}
- Recent History:
{history}

Latest Question: "{question}"

Instructions:
- Return ONLY the exact classification text: 'sql_with_context', 'rag', 'chat', or 'unauthorized'.
- Do NOT return any preamble, code blocks, or formatting."""
            
            response = llm.invoke(prompt)
            classification = response.content.strip().lower()
            
            # Extract just the classification keyword
            for valid_category in ['sql_with_context', 'rag', 'unauthorized', 'chat']:
                if valid_category in classification:
                    # Sanity check against missing infrastructure
                    if valid_category == 'sql_with_context' and not has_db:
                        return 'rag' if has_docs else 'chat'
                    if valid_category == 'rag' and not has_docs:
                        return 'sql_with_context' if has_db else 'chat'
                    return valid_category
            
            # Additional fallback if LLM returns "sql" instead of "sql_with_context"
            if 'sql' in classification:
                return 'sql_with_context' if has_db else ('rag' if has_docs else 'chat')

        except Exception as e:
            print(f"LLM Classification failed, falling back to keywords: {e}")
            pass

    # Keyword fallback
    q = question.lower()
    
    if has_db and any(kw in q for kw in FORBIDDEN_INTENT_KEYWORDS):
        return "unauthorized"

    if has_db and any(kw in q for kw in SQL_KEYWORDS):
        return "sql_with_context"

    if has_docs and any(kw in q for kw in DOC_KEYWORDS):
        return "rag"

    # Fallback: if DB configured, try SQL; else RAG; else chat
    if has_db:
        return "sql_with_context"
    if has_docs:
        return "rag"
    return "chat"
