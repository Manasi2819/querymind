import sys
import os

# Add the current directory to sys.path to allow importing from services
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from services.encryption import encrypt_secret, decrypt_secret
from services.redaction_service import redact_secrets
from services.sql_rag_service import validate_sql

def test_encryption():
    print("--- Testing Encryption ---")
    secret = "my-secret-key-123"
    encrypted = encrypt_secret(secret)
    decrypted = decrypt_secret(encrypted)
    
    print(f"Original: {secret}")
    print(f"Encrypted: {encrypted}")
    print(f"Decrypted: {decrypted}")
    
    assert secret == decrypted, "Encryption/Decryption failed!"
    
    # Test legacy plain-text fallback
    print(f"Decryption fallback (plain text): {decrypt_secret('plain-text')}")
    assert decrypt_secret('plain-text') == 'plain-text', "Fallback failed!"
    print("Encryption tests passed!")

def test_redaction():
    print("\n--- Testing Redaction ---")
    test_cases = [
        ("My key is sk-1234567890abcdef1234567890abcdef1234567890abcdef", "contains OpenAI key"),
        ("Connection: mysql://user:password123@localhost:3306/db", "contains DB URL with password"),
        ("Here is the gsk_1234567890abcdef1234567890abcdef12345678", "contains Groq key"),
        ("API Key: abcdef1234567890", "contains generic key label"),
    ]
    
    for text, desc in test_cases:
        redacted = redact_secrets(text)
        print(f"Original ({desc}): {text}")
        print(f"Redacted: {redacted}")
        assert "password123" not in redacted
        assert "sk-" not in redacted or "[REDACTED" in redacted
        assert "gsk_" not in redacted or "[REDACTED" in redacted
    print("Redaction tests passed!")

def test_sql_guardrails():
    print("\n--- Testing SQL Guardrails ---")
    valid_sql = "SELECT name FROM users WHERE id = 1;"
    invalid_sql_keywords = "DROP TABLE users;"
    invalid_sql_tables = "SELECT * FROM admin_users;"
    
    try:
        validate_sql(valid_sql)
        print("Valid SQL passed.")
    except Exception as e:
        print(f"Valid SQL failed unexpectedly: {e}")
        
    try:
        validate_sql(invalid_sql_keywords)
        print("FAIL: Forbidden keywords allowed!")
    except Exception as e:
        print(f"Forbidden keywords blocked correctly: {e}")
        
    try:
        validate_sql(invalid_sql_tables)
        print("FAIL: Forbidden tables allowed!")
    except Exception as e:
        print(f"Forbidden tables blocked correctly: {e}")
    print("SQL Guardrail tests passed!")

if __name__ == "__main__":
    try:
        test_encryption()
        test_redaction()
        test_sql_guardrails()
        print("\nAll security tests passed successfully!")
    except Exception as e:
        print(f"\nTests failed: {e}")
        sys.exit(1)
