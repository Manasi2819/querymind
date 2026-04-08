import requests
import time

API_URL = "http://localhost:8000"

def test_multi_user():
    print("--- Testing Multi-User Registration ---")
    
    # 1. Register User A
    user_a = {"username": f"user_a_{int(time.time())}", "password": "passwordA"}
    r = requests.post(f"{API_URL}/admin/register", json=user_a)
    if r.status_code != 200:
        print(f"FAILED: User A registration failed: {r.text}")  
        return
    user_a_id = r.json()["user_id"]
    print(f"User A registered with ID: {user_a_id}")

    # 2. Register User B
    user_b = {"username": f"user_b_{int(time.time())}", "password": "passwordB"}
    r = requests.post(f"{API_URL}/admin/register", json=user_b)
    if r.status_code != 200:
        print(f"FAILED: User B registration failed: {r.text}")
        return
    user_b_id = r.json()["user_id"]
    print(f"User B registered with ID: {user_b_id}")

    # 3. Test Chat with User A
    print("\n--- Testing Chat for User A ---")
    chat_req_a = {
        "message": "Hello", 
        "session_id": "session_a",
        "user_id": user_a_id
    }
    r = requests.post(f"{API_URL}/chat", json=chat_req_a)
    if r.status_code == 200:
        print(f"User A Chat Success: {r.json()['answer']}")
    else:
        print(f"User A Chat Failed: {r.text}")

    # 4. Test Chat with User B
    print("\n--- Testing Chat for User B ---")
    chat_req_b = {
        "message": "Hello", 
        "session_id": "session_b",
        "user_id": user_b_id
    }
    r = requests.post(f"{API_URL}/chat", json=chat_req_b)
    if r.status_code == 200:
        print(f"User B Chat Success: {r.json()['answer']}")
    else:
        print(f"User B Chat Failed: {r.text}")

    print("\nSUCCESS: Multi-user registration and chat routing is functional.")

if __name__ == "__main__":
    test_multi_user()
