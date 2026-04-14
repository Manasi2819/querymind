import sqlite3
import os

db_path = r'c:\Users\HP\hp\DocumentsN\chatbot1\querymind\backend\querymind_metadata.db'

if not os.path.exists(db_path):
    print(f"Error: Database not found at {db_path}")
    exit(1)

conn = sqlite3.connect(db_path)
cursor = conn.cursor()

try:
    cursor.execute("UPDATE uploaded_files SET file_type = 'data_dictionary' WHERE file_type = 'knowledge_base'")
    conn.commit()
    print(f"Updated {cursor.rowcount} records from 'knowledge_base' to 'data_dictionary'.")
except Exception as e:
    print(f"Error during migration: {e}")
finally:
    conn.close()
