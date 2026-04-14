import chromadb
import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import get_settings

def find_file_chunks():
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    
    # Check collections
    collections = ['user_1_general_document', 'user_1_data_dictionary', 'user_1_document', 'user_1_knowledge_base']
    
    for name in collections:
        try:
            col = client.get_collection(name)
            # Find all unique sources in this collection
            results = col.get()
            if results and results['metadatas']:
                sources = set(m.get('source') for m in results['metadatas'] if m)
                print(f"Collection: {name} | Documents: {len(results['ids'])} | Sources: {sources}")
                
                # If TPVRM is in there, let's see a chunk
                for m in results['metadatas']:
                    if m and 'TPVRM' in str(m.get('source')):
                        # Get indices of documents with this source
                        idx = results['metadatas'].index(m)
                        print(f"  FOUND {m.get('source')} CHUNK: {results['documents'][idx][:500]}...")
                        break
        except Exception as e:
            print(f"Collection {name} error: {e}")

if __name__ == "__main__":
    find_file_chunks()
