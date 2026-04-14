import chromadb
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import get_settings

def investigate():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    
    collections = ['user_1_general_document', 'user_1_data_dictionary', 'user_1_document', 'user_1_knowledge_base']
    
    print("--- Collection Status ---")
    for name in collections:
        try:
            col = client.get_collection(name)
            count = col.count()
            print(f"{name}: {count} documents")
            if count > 0:
                # Peek at the first document's metadata
                peek = col.peek(1)
                print(f"  Peek metadata: {peek['metadatas']}")
        except Exception as e:
            print(f"{name}: Not found or error: {e}")

    # Now let's try a search for 'problem statement'
    from services.llm_service import get_embed_model
    embed_model = get_embed_model()
    query_embedding = embed_model.embed_query("problem statement")
    
    print("\n--- Search Results for 'problem statement' ---")
    for name in collections:
        try:
            col = client.get_collection(name)
            res = col.query(query_embeddings=[query_embedding], n_results=3)
            if res and res['documents'] and res['documents'][0]:
                print(f"Results in {name}:")
                for i, doc in enumerate(res['documents'][0]):
                    print(f"  [{i}] {doc[:200]}...")
            else:
                print(f"No results in {name}")
        except:
            pass

if __name__ == "__main__":
    investigate()
