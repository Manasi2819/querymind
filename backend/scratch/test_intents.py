import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.intent_classifier import classify_intent

def test_intent_guardrails():
    print("--- Running Strict Intent Guardrail Tests ---")
    
    # We'll test with has_db=True to simulate the live environment
    test_cases = [
        ("Drop the record of LR Transporter", "unauthorized"),
        ("Delete all users", "unauthorized"),
        ("Update the price of item 1 to 500", "unauthorized"),
        ("Insert a new customer named John", "unauthorized"),
        ("Remove the database", "unauthorized"),
        ("Clear all records", "unauthorized"),
        ("Show me all users", "sql"), # This should still be allowed
        ("What is the counts of orders", "sql"), # Still allowed
        ("Explain how the billing works", "rag"), # RAG still allowed
    ]
    
    for question, expected_intent in test_cases:
        try:
            # We skip LLM provider here for unit testing to test the keyword logic first
            intent = classify_intent(question, has_db=True, has_docs=True)
            if intent == expected_intent:
                print(f"PASSED: '{question}' -> {intent}")
            else:
                print(f"FAILED: '{question}' -> Got {intent}, Expected {expected_intent}")
        except Exception as e:
            print(f"ERROR: '{question}' - {e}")

if __name__ == "__main__":
    test_intent_guardrails()
