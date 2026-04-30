import chromadb
from services.llm_service import get_embed_model
from config import get_settings

settings = get_settings()
client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
collection = client.get_collection(name="user_1_sql_metadata")

# Search for employee table
results = collection.get(where={"table_name": "employee"})
if results["documents"]:
    print(results["documents"][0])
else:
    print("Employee table metadata not found")
