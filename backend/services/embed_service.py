import chromadb
from langchain_chroma import Chroma
from services.llm_service import get_embed_model
from config import get_settings

settings = get_settings()

def get_vector_store(collection_name: str) -> Chroma:
    """Returns a Chroma vector store for the given collection."""
    # Using local PersistentClient because Docker is not available in the current environment
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    return Chroma(
        client=client,
        collection_name=collection_name,
        embedding_function=get_embed_model(),
    )

def add_documents(texts: list[str], metadatas: list[dict], collection_name: str):
    """Embeds and stores document chunks."""
    from langchain_core.documents import Document
    store = get_vector_store(collection_name)
    docs = [Document(page_content=t, metadata=m) for t, m in zip(texts, metadatas)]
    store.add_documents(docs)
    return len(docs)

def similarity_search(query: str, collection_name: str, k: int = 4) -> list:
    """Returns top-k relevant chunks for a query."""
    store = get_vector_store(collection_name)
    return store.similarity_search(query, k=k)

def delete_collection(collection_name: str):
    """Deletes all vectors in a collection (called when files are re-uploaded)."""
    # Using local PersistentClient instead of Docker-based HttpClient
    client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
    try:
        client.delete_collection(collection_name)
    except Exception:
        pass   # collection may not exist yet
