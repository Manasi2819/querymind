import requests
import json
import time
import os

BASE_URL = "http://localhost:8000"
ADMIN_USER = "admin"
ADMIN_PASS = "admin123"

def verify():
    print("--- 1. Authenticating ---")
    resp = requests.post(f"{BASE_URL}/admin/token", data={
        "username": ADMIN_USER,
        "password": ADMIN_PASS
    })
    if resp.status_code != 200:
        print(f"Login failed: {resp.text}")
        return
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Login successful.")

    print("\n--- 2. Uploading test_doc.txt ---")
    # Ensure test_doc.txt exists
    doc_path = "test_doc.txt"
    if not os.path.exists(doc_path):
        with open(doc_path, "w") as f:
            f.write("QueryMind features:\n1. SQL RAG\n2. Doc RAG\n3. Chat Memory\n4. Deployment")
    
    with open(doc_path, "rb") as f:
        resp = requests.post(
            f"{BASE_URL}/admin/upload",
            headers=headers,
            files={"file": (doc_path, f, "text/plain")},
            data={"file_type": "document"}
        )
    
    if resp.status_code != 200:
        print(f"Upload failed: {resp.text}")
        return
    print(f"Upload success: {resp.json()}")

    print("\n--- 3. Testing Context-Aware Chat ---")
    session_id = f"test_session_{int(time.time())}"
    
    # 3a. Initial Question
    quest1 = "What are the features of QueryMind according to the doc?"
    print(f"User: {quest1}")
    resp = requests.post(f"{BASE_URL}/chat", json={
        "message": quest1,
        "session_id": session_id
    })
    ans1 = resp.json()["answer"]
    print(f"Assistant: {ans1}")

    # 3b. Follow-up Question (Context check)
    quest2 = "Tell me more about the third one."
    print(f"\nUser: {quest2}")
    resp = requests.post(f"{BASE_URL}/chat", json={
        "message": quest2,
        "session_id": session_id
    })
    ans2 = resp.json()["answer"]
    print(f"Assistant: {ans2}")

    print("\n--- VERIFICATION COMPLETE ---")

if __name__ == "__main__":
    verify()
