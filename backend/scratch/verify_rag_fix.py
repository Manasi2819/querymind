import os
import sys

# Add backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from services.rag_service import answer_from_docs

def verify_fix():
    question = "What is problem statement defined?"
    tenant_id = "user_1"
    
    # Simulating the chat router call
    print(f"Querying: {question}")
    
    # Let's see what chunks it finds
    import chromadb
    from config import get_settings
    settings = get_settings()
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    col = client.get_collection("user_1_general_document")
    from services.llm_service import get_embed_model
    embed_model = get_embed_model()
    query_embedding = embed_model.embed_query(question)
    res = col.query(query_embeddings=[query_embedding], n_results=5)
    print("\n--- Retrieved Chunks ---")
    for i, doc in enumerate(res['documents'][0]):
        print(f"[{i}] {doc[:300]}...")
    
    answer = answer_from_docs(
        question=question,
        tenant_id=tenant_id,
        file_type="general_document",  # This is what chat.py now sends
        llm_provider="ollama",          # Adjust if needed
        model="phi3:mini"
    )
    
    print("\n--- Answer ---")
    print(answer)
    print("--------------")

if __name__ == "__main__":
    verify_fix()
