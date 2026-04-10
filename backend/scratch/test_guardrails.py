import sys
import os

# Add the backend directory to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.sql_rag_service import validate_sql, execute_query

def test_guardrails():
    print("--- Running SQL Guardrail Tests ---")
    
    safe_queries = [
        "SELECT * FROM users",
        "SELECT name, email FROM contacts WHERE id = 1",
        "SELECT last_updated FROM metadata",  # Should not match 'UPDATE' because it's part of a word
        "WITH sales AS (SELECT * FROM orders) SELECT SUM(total) FROM sales"
    ]
    
    unsafe_queries = [
        "DELETE FROM users",
        "UPDATE settings SET value = 0",
        "INSERT INTO logs (msg) VALUES ('test')",
        "DROP TABLE customers",
        "SELECT * FROM users; DELETE FROM users", # Sequential injection
        "CREATE TABLE hack (id int)",
        "TRUNCATE TABLE important_data"
    ]
    
    print("\nTesting Safe Queries (should pass):")
    for q in safe_queries:
        try:
            validate_sql(q)
            print(f"PASSED: {q}")
        except Exception as e:
            print(f"FAILED (False Positive): {q} - Error: {e}")
            
    print("\nTesting Unsafe Queries (should be blocked):")
    for q in unsafe_queries:
        try:
            validate_sql(q)
            print(f"FAILED (Missed Guardrail): {q}")
        except Exception as e:
            print(f"BLOCKED: {q} - Reason: {e}")

if __name__ == "__main__":
    test_guardrails()
