import chromadb
from langchain_chroma import Chroma
from services.llm_service import get_embed_model
from config import get_settings

settings = get_settings()

def get_vector_store(collection_name: str) -> Chroma:
    """Returns a Chroma vector store for the given collection."""
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=get_embed_model(),
    )

def add_documents(texts: list, metadatas: list, collection_name: str) -> int:
    """Embeds and saves documents to a persistent Chroma collection."""
    store = get_vector_store(collection_name)
    store.add_texts(list(texts), metadatas=metadatas)
    return len(texts)

def delete_by_metadata(collection_name: str, filter_dict: dict):
    """Deletes documents from a collection that match the metadata filter."""
    try:
        store = get_vector_store(collection_name)
        # ChromaDB as_retriever doesn't expose delete directy in LangChain wrapper
        # We access the underlying collection
        client = store._client
        collection = client.get_collection(collection_name)
        collection.delete(where=filter_dict)
    except Exception as e:
        # If collection doesn't exist, ignore
        print(f"Delete mismatch: {str(e)}")

def similarity_search(query: str, collection_name: str, k: int = 4, filter_dict: dict = None) -> list:
    """Returns top-k relevant chunks for a query with optional metadata filtering."""
    store = get_vector_store(collection_name)
    return store.similarity_search(query, k=k, filter=filter_dict)

def delete_collection(collection_name: str):
    """Deletes all vectors in a collection (called when files are re-uploaded)."""
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass   # collection may not exist yet
