from sqlalchemy import create_engine, inspect
from cryptography.fernet import Fernet
import json
import sqlite3

FERNET_KEY = b"REMOVED_KEY_FOR_SECURITY===================="
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
