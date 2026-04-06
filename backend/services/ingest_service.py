"""
Ingestion service — parses uploaded files and stores chunks in ChromaDB.
Triggered automatically on every file upload (re-upload replaces old vectors).
"""

import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, CSVLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from services.embed_service import add_documents, delete_collection
from config import get_settings

settings = get_settings()

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

def load_file(filepath: str) -> list:
    """Loads a file and returns LangChain Document objects."""
    ext = Path(filepath).suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(filepath)
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(filepath)
    elif ext == ".csv":
        loader = CSVLoader(filepath)
    else:
        loader = TextLoader(filepath, encoding="utf-8")
    return loader.load()

def ingest_file(filepath: str, tenant_id: str, file_type: str = "document") -> dict:
    """
    Full ingestion pipeline for one file:
    1. Load → 2. Split → 3. Delete old collection → 4. Embed + store
    Returns status dict.
    """
    try:
        collection_name = f"{tenant_id}_{file_type}"
        docs = load_file(filepath)
        chunks = SPLITTER.split_documents(docs)

        texts = [c.page_content for c in chunks]
        metadatas = [
            {**c.metadata, "tenant_id": tenant_id, "file_type": file_type,
             "source": Path(filepath).name}
            for c in chunks
        ]

        # Re-upload replaces old vectors completely
        delete_collection(collection_name)
        count = add_documents(texts, metadatas, collection_name)

        return {"status": "done", "chunks": count, "message": f"Indexed {count} chunks"}

    except Exception as e:
        return {"status": "error", "chunks": 0, "message": str(e)}
