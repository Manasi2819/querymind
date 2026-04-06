from services.intent_classifier import classify_intent

def test_classify_intent_sql():
    assert classify_intent("how many users do we have?", True, True) == "sql"
    assert classify_intent("what is the total average revenue?", True, False) == "sql"

def test_classify_intent_rag():
    assert classify_intent("what does status 5 mean?", True, True) == "rag"
    assert classify_intent("explain the data dictionary", False, True) == "rag"

def test_classify_intent_fallback():
    # If it doesn't match a quick keyword but has DB, it defaults to SQL
    assert classify_intent("give me the system overview", True, True) == "sql"
    # If no DB but has docs, defaults to RAG
    assert classify_intent("who is the user", False, True) == "rag"
    # If neither DB nor Docs, defaults to general
    assert classify_intent("what is the capitol of france?", False, False) == "general"
