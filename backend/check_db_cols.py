from sqlalchemy import create_engine, inspect
from cryptography.fernet import Fernet
import json
import sqlite3

import sys
import os
# Add the parent directory to the path so we can import config
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from config import get_settings

settings = get_settings()
if not settings.fernet_key:
    raise ValueError("FERNET_KEY is not configured")
FERNET_KEY = settings.fernet_key.encode('utf-8')
cipher = Fernet(FERNET_KEY)

conn = sqlite3.connect('querymind_metadata.db')
cursor = conn.cursor()
cursor.execute("SELECT db_config FROM admin_settings WHERE user_id = 1")
row = cursor.fetchone()
cfg = json.loads(row[0])
url = cipher.decrypt(cfg["url"].encode()).decode()

engine = create_engine(url)
inspector = inspect(engine)
columns = inspector.get_columns("employee")
print([c["name"] for c in columns])
conn.close()
