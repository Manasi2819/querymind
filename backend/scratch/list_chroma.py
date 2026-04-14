import chromadb
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import get_settings

def list_all():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    
    print("--- All Collections ---")
    # list_collections() returns a list of Collection objects or names depending on version
    cols = client.list_collections()
    for c in cols:
        name = c.name if hasattr(c, 'name') else str(c)
        try:
            count = client.get_collection(name).count()
            print(f"Collection: {name} | Count: {count}")
        except:
            print(f"Collection: {name} | Error getting count")

if __name__ == "__main__":
    list_all()
