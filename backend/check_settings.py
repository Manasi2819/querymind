import sqlite3
import json
conn = sqlite3.connect('querymind_metadata.db')
cursor = conn.cursor()
cursor.execute("SELECT db_config FROM admin_settings WHERE user_id = 1")
row = cursor.fetchone()
if row:
    print(row[0])
else:
    print("No settings found for user 1")
conn.close()
