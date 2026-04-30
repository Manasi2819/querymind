import sqlite3
try:
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute("SELECT version_num FROM alembic_version")
    print(cursor.fetchone()[0])
    conn.close()
except Exception as e:
    print(f"Error: {e}")
