import requests
import uuid

BASE_URL = "http://localhost:8000"
SESSION_ID = str(uuid.uuid4())

def test_query(message, expected_answer=None, description=""):
    print(f"\n--- Testing: {description} ---")
    print(f"Query: {message}")
    
    payload = {
        "message": message,
        "session_id": SESSION_ID,
        "user_id": 1
    }
    
    try:
        response = requests.post(f"{BASE_URL}/chat", json=payload)
        response.raise_for_status()
        data = response.json()
        answer = data.get("answer")
        source = data.get("source")
        
        print(f"Response: {answer}")
        print(f"Source: {source}")
        
        if expected_answer and expected_answer in answer:
            print("âœ… PASS")
        elif expected_answer:
            print(f"âŒ FAIL: Expected '{expected_answer}' to be in '{answer}'")
        else:
            print("âœ… Received response (manual check might be needed)")
            
    except Exception as e:
        print(f"âŒ ERROR: {e}")

if __name__ == "__main__":
    # Test 1: Forbidden SQL Keyword (Pre-emptive)
    test_query(
        "DELETE FROM users", 
        expected_answer="I cannot do that action, I can only fetch data and show it.",
        description="Forbidden SQL Keyword (DELETE)"
    )
    
    # Test 2: Forbidden SQL Keyword (Pre-emptive, case insensitive)
    test_query(
        "Drop the products table please", 
        expected_answer="I cannot do that action, I can only fetch data and show it.",
        description="Forbidden SQL Keyword (DROP)"
    )

    # Test 3: General Knowledge (Chat rejection)
    test_query(
        "Who is the president of the United States?", 
        expected_answer="I don't have answer to that.",
        description="General Knowledge Rejection"
    )

    # Test 4: Greeting (Chat rejection)
    test_query(
        "Hello, how are you today?", 
        expected_answer="I don't have answer to that.",
        description="Greeting Rejection"
    )

    # Test 5: Valid SQL Query (Should still work)
    # Note: This might fail if DB is not configured, but the source should be 'sql' or 'rag' or 'system' error, not 'chat' rejection
    test_query(
        "How many users are there?", 
        description="Valid Information Query"
    )
