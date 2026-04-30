import sqlite3
conn = sqlite3.connect('querymind_metadata.db')
cursor = conn.cursor()
cursor.execute("UPDATE alembic_version SET version_num = '910bc7f3e15f'")
conn.commit()
conn.close()
print("Alembic version reset to 910bc7f3e15f")
