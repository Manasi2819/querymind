"""
SQL Metadata Service — fetches and embeds database schema information.
"""

from sqlalchemy import create_engine, inspect
import chromadb
from chromadb.config import Settings
from config import get_settings
from services.llm_service import get_embed_model

settings = get_settings()

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

def fetch_db_schema(connection_url: str) -> list:
    """
    Uses SQLAlchemy's inspector to fetch table and column metadata.
    Returns a list of dicts: [{'table': '...', 'columns': '...', 'description': '...'}]
    """
    from services.database_connection import connect_db
    engine = connect_db(connection_url)
    inspector = inspect(engine)
    
    schema_metadata = []
    tables = inspector.get_table_names()
    
    for table in tables:
        columns = inspector.get_columns(table)
        col_info = [f"{c['name']} ({c['type']})" for c in columns]
        
        # Primary Keys
        pk = inspector.get_pk_constraint(table).get('constrained_columns', [])
        
        # Foreign Keys
        fk = inspector.get_foreign_keys(table)
        fk_info = [f"{f['constrained_columns']} -> {f['referred_table']}.{f['referred_columns']}" for f in fk]

        metadata_text = f"Table: {table}\n"
        metadata_text += f"Columns: {', '.join(col_info)}\n"
        if pk:
            metadata_text += f"Primary Key: {', '.join(pk)}\n"
        if fk_info:
            metadata_text += f"Foreign Keys: {'; '.join(fk_info)}"
            
        schema_metadata.append({
            "table": table,
            "text": metadata_text,
            "metadata": {"table_name": table}
        })
        
    return schema_metadata

def index_db_metadata(connection_url: str, tenant_id: str):
    """
    Fetches schema and stores it in ChromaDB for later retrieval during SQL generation.
    """
    schema_items = fetch_db_schema(connection_url)
    if not schema_items:
        return 0
        
    client = get_chroma_client()
    collection_name = f"{tenant_id}_sql_metadata"
    
    # Reset existing metadata
    try:
        client.delete_collection(name=collection_name)
    except:
        pass
        
    collection = client.create_collection(name=collection_name)
    
    ids = [f"table_{i}" for i in range(len(schema_items))]
    documents = [item["text"] for item in schema_items]
    metadatas = [item["metadata"] for item in schema_items]
    
    # We use the same embedding model as RAG
    embed_model = get_embed_model()
    embeddings = embed_model.embed_documents(documents)
    
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
    return len(schema_items)
