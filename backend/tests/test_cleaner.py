import sys
import os

# Mocking parts of the system to test the cleaning logic
def clean_key(key: str) -> str:
    key = str(key).strip()
    if " " in key:
        parts = key.split()
        for part in parts:
            if part.startswith(("sk-", "gsk_", "AIza")): # Common prefixes
                key = part
                break
    return key

def test_cleaner():
    print("--- Testing API Key Cleaner ---")
    test_cases = [
        ("  sk-12345  ", "sk-12345"),
        ("grok api key - gsk_ABC123", "gsk_ABC123"),
        ("my openai key is sk-XYZ789   ", "sk-XYZ789"),
        ("AIza_GOOGLE_KEY", "AIza_GOOGLE_KEY"),
        ("just_a_key", "just_a_key"),
    ]
    
    for input_key, expected in test_cases:
        result = clean_key(input_key)
        print(f"Input: '{input_key}' -> Result: '{result}'")
        assert result == expected, f"Failed for {input_key}"
    
    print("\n[PASS] API Key Cleaner works correctly!")

if __name__ == "__main__":
    test_cleaner()
