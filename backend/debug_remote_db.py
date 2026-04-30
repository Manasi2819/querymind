import sqlite3
import json
from cryptography.fernet import Fernet
import os
from sqlalchemy import create_engine, inspect

# Get Fernet Key
# Try to find it in .env or settings
# In the previous view_file of .env:
# FERNET_KEY=REMOVED_KEY_FOR_SECURITY====================
FERNET_KEY = b"REMOVED_KEY_FOR_SECURITY===================="
cipher = Fernet(FERNET_KEY)

conn = sqlite3.connect('querymind_metadata.db')
cursor = conn.cursor()
cursor.execute("SELECT db_config FROM admin_settings WHERE user_id = 1")
row = cursor.fetchone()
if row:
    cfg = json.loads(row[0])
    enc_url = cfg["url"]
    url = cipher.decrypt(enc_url.encode()).decode()
    print(f"URL decrypted: {url[:20]}...")
    
    try:
        engine = create_engine(url)
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        print(f"Tables in DB: {tables}")
        
        if "employee" in tables:
            cols = inspector.get_columns("employee")
            print(f"Columns in employee: {[c['name'] for c in cols]}")
        else:
            print("employee table not found in this DB.")
    except Exception as e:
        print(f"Failed to connect: {e}")
conn.close()
