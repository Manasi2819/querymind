import sqlite3
conn = sqlite3.connect('querymind_metadata.db')
cursor = conn.cursor()
cursor.execute("SELECT user_id FROM chat_sessions WHERE id = 'ae60e1b8-5a29-46f3-8050-d4b770b97ad2'")
row = cursor.fetchone()
print(row[0] if row else "Not found")
conn.close()
