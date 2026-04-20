import chromadb
import sys
import os

# Ensure we can import from the parent directory if needed
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))

from config import get_settings

def reset_user_store(user_id: int):
    settings = get_settings()
    print(f"Connecting to ChromaDB at: {settings.chroma_persist_dir}")
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    
    tenant_id = f"user_{user_id}"
    # Collections we want to clear to ensure a fresh start for the new pipeline
    collections = [
        f"{tenant_id}_document",
        f"{tenant_id}_knowledge_base"
    ]
    
    for coll_name in collections:
        try:
            print(f"Attempting to delete collection: {coll_name}...")
            client.delete_collection(name=coll_name)
            print(f"Successfully deleted {coll_name}")
        except Exception as e:
            # If collection doesn't exist, ChromaDB raises an error. We catch it here.
            print(f"Result for {coll_name}: Collection not found or already empty.")

if __name__ == "__main__":
    # By default, resetting for user_id 1
    target_user = 1
    print(f"--- Vector Store Reset Tool ---")
    reset_user_store(user_id=target_user)
    print(f"--- Reset Complete ---")
    print(f"You can now re-upload your JSON, CSV, or SQL files to build the new context-aware pipeline.")
