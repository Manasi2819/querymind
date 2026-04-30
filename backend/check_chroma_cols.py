import chromadb
from config import get_settings

settings = get_settings()
client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_collection(name="user_1_sql_metadata")

results = collection.get(where={"table_name": "employee"})
if results["documents"]:
    doc = results["documents"][0]
    for line in doc.split("\n"):
        if line.startswith("Columns:"):
            print(line)
else:
    print("Employee table metadata not found")
