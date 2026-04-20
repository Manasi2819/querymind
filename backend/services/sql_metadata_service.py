"""
SQL Metadata Service — fetches and embeds database schema information.
"""

from sqlalchemy import create_engine, inspect
import chromadb
from config import get_settings
from services.llm_service import get_embed_model, get_llm

settings = get_settings()

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

def generate_table_interpretation(table_name: str, columns: list, llm_config: dict = None) -> str:
    """
    Uses LLM to generate a natural language meaning for the table.
    """
    print(f"Generating interpretation for table: {table_name}...")
    # Extract just names for the prompt
    col_names = [c.split(" (")[0] for c in columns]
    
    llm = get_llm(**llm_config) if llm_config else get_llm()
    
    # Ultra-concise prompt for speed on local LLMs
    prompt = f"In one short sentence, what is the table '{table_name}' for given columns {','.join(col_names)}? Answer starts: 'This table...'"
    
    try:
        # Use a short timeout to prevent total hang (if your LLM is slow)
        response = llm.invoke(prompt, timeout=15)
        return response.content.strip()
    except Exception as e:
        print(f"  [AI Timeout/Skip] Table: {table_name}. Using default.")
        return f"This table stores data for {table_name}."

def fetch_db_schema(connection_url: str, llm_config: dict = None) -> list:
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
        print(f"Processing table: {table}")
        columns = inspector.get_columns(table)
        col_info = [f"{c['name']} ({c['type']})" for c in columns]
        
        # New: Generate AI interpretation
        meaning = generate_table_interpretation(table, col_info, llm_config)
        print(f"Interpretation: {meaning}")
        
        # Primary Keys
        pk = inspector.get_pk_constraint(table).get('constrained_columns', [])
        
        # Foreign Keys
        fk = inspector.get_foreign_keys(table)
        fk_info = [f"{f['constrained_columns']} -> {f['referred_table']}.{f['referred_columns']}" for f in fk]

        metadata_text = f"Table: {table}\n"
        metadata_text += f"Description: {meaning}\n"
        metadata_text += f"Columns: {', '.join(col_info)}\n"
        if pk:
            metadata_text += f"Primary Key: {', '.join(pk)}\n"
        if fk_info:
            metadata_text += f"Foreign Keys: {'; '.join(fk_info)}"
            
        schema_metadata.append({
            "table": table,
            "text": metadata_text,
            "metadata": {"table_name": table, "description": meaning}
        })
        
    return schema_metadata

def index_db_metadata(connection_url: str, tenant_id: str, llm_config: dict = None):
    """
    Fetches schema and stores it in ChromaDB for later retrieval during SQL generation.
    """
    schema_items = fetch_db_schema(connection_url, llm_config)
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
    base_url = llm_config.get("base_url") if llm_config else None
    embed_model = get_embed_model(base_url=base_url)
    embeddings = embed_model.embed_documents(documents)
    
    collection.add(
        ids=ids,
        documents=documents,
        embeddings=embeddings,
        metadatas=metadatas
    )
    
    return len(schema_items)
