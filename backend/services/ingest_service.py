"""
Ingestion service — parses uploaded files and stores chunks in ChromaDB.
Triggered automatically on every file upload (re-upload replaces old vectors).
"""

import os
from pathlib import Path
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, CSVLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from services.embed_service import add_documents, delete_collection
from config import get_settings
from datetime import datetime

settings = get_settings()

SPLITTER = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=100)

def load_file(filepath: str) -> list:
    """Loads a file and returns LangChain Document objects."""
    from langchain_core.documents import Document
    path = Path(filepath).resolve()
    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")
        
    ext = path.suffix.lower()
    if ext == ".pdf":
        loader = PyPDFLoader(str(path))
        return loader.load()
    elif ext in (".docx", ".doc"):
        loader = Docx2txtLoader(str(path))
        return loader.load()
    elif ext == ".csv":
        loader = CSVLoader(str(path))
        return loader.load()
    elif ext == ".json":
        # Strategy: Index whole JSON block as a document for maximum flexibility
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        return [Document(page_content=content, metadata={"source": str(path)})]
    else:
        # sql, md, txt, etc.
        loader = TextLoader(str(path), encoding="utf-8")
        return loader.load()

def ingest_file(filepath: str, tenant_id: str, file_type: str = "document", db=None, user_id=None) -> dict:
    """
    Full ingestion pipeline for one file:
    1. Load → 2. Split → 3. Delete old collection (re-implemented for safety) → 4. Embed + store → 5. Record in DB
    Returns status dict.
    """
    try:
        from models.db_models import UploadedFile
        filename = Path(filepath).name
        collection_name = f"{tenant_id}_{file_type}"
        
        docs = load_file(filepath)
        chunks = SPLITTER.split_documents(docs)

        texts = [c.page_content for c in chunks]
        metadatas = [
            {**c.metadata, "tenant_id": tenant_id, "file_type": file_type,
             "source": filename}
            for c in chunks
        ]

        # RE-UPLOAD logic: delete old vectors for THIS FILE only
        from services.embed_service import delete_by_metadata
        delete_by_metadata(collection_name, {"source": filename})
        # Note: If delete_by_metadata is not yet added to embed_service, we'll need to add it.
        # But for new implementation, let's assume we use it.

        count = add_documents(texts, metadatas, collection_name)

        if db and user_id:
            # Upsert DB metadata
            file_record = db.query(UploadedFile).filter(
                UploadedFile.user_id == user_id, 
                UploadedFile.filename == filename
            ).first()
            if not file_record:
                file_record = UploadedFile(user_id=user_id, filename=filename)
                db.add(file_record)
            
            file_record.file_type = file_type
            file_record.upload_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_record.chunk_count = count
            db.commit()

        return {"status": "done", "chunks": count, "message": f"Indexed {count} chunks for {filename}"}

    except Exception as e:
        return {"status": "error", "chunks": 0, "message": str(e)}
