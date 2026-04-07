import requests

API_URL = "http://localhost:8000"

def test_admin_persistence():
    print("Testing Admin Persistence...")
    
    # 1. Login
    login_data = {"username": "admin", "password": "admin123"}
    r = requests.post(f"{API_URL}/admin/token", data=login_data)
    if r.status_code != 200:
        print(f"FAILED: Login failed: {r.text}")
        return False
    
    token = r.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("Logged in successfully.")

    # 2. Save DB Config (Mocking a valid-ish config)
    # Note: We need a real DB or mock test_connection in admin.py to bypass connection test
    # but the connection test is run in save_db_config.
    # Let's use a sqlite connection that should succeed.
    db_config = {
        "db_type": "sqlite",
        "database": "smoke_test.db"
    }
    r = requests.post(f"{API_URL}/admin/db-config", json=db_config, headers=headers)
    
    if r.status_code != 200:
        print(f"FAILED: Save DB config failed: {r.text}")
        # Note: If it fails because of connection, it's expected if smoke_test.db doesn't exist
        # But we want to see if it reaches the DB.
        # Let's check if it's 400 (connection error) or something else.
        if r.status_code == 400:
             print("Note: Connection failed as expected, but reached the endpoint.")
        else:
             return False

    # 3. Retrieve DB Config
    r = requests.get(f"{API_URL}/admin/db-config", headers=headers)
    if r.status_code != 200:
        print(f"FAILED: Get DB config failed: {r.text}")
        return False
    
    config = r.json()
    print(f"Retrieved Config: {config}")
    
    if config.get("configured"):
        print("SUCCESS: Persistence working!")
        return True
    else:
        print("FAILED: Config not found in DB.")
        return False

if __name__ == "__main__":
    test_admin_persistence()
