import requests
import json

url = "http://localhost:8000/chat"
headers = {"Content-Type": "application/json"}
payload = {
    "session_id": "test-session-123",
    "user_id": "1",
    "message": "what is the employment status of each of them along with their names"
}

try:
    response = requests.post(url, json=payload, headers=headers)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
except Exception as e:
    print(f"Error: {e}")
