"""
SQL RAG Service — implementation of the Vanna-style "Metadata RAG" pipeline.
Retrieves relevant tables, generates SQL via LLM, and executes the query.
"""

import pandas as pd
from sqlalchemy import create_engine, text
import chromadb
from config import get_settings
from services.llm_service import get_llm, get_embed_model

settings = get_settings()

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.chroma_db_path)

def retrieve_relevant_schema(query: str, tenant_id: str, k: int = 3) -> str:
    """
    Search ChromaDB for the most relevant table/column metadata chunks.
    """
    client = get_chroma_client()
    collection_name = f"{tenant_id}_sql_metadata"
    
    try:
        collection = client.get_collection(name=collection_name)
    except:
        return "No database metadata found. Please fetch schema in Admin first."

    # Embed the query
    embed_model = get_embed_model()
    query_embedding = embed_model.embed_query(query)
    
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=k
    )
    
    if not results or not results['documents'][0]:
        return "No relevant metadata found for this query."
        
    context = "\n\n".join(results['documents'][0])
    return context

def generate_sql(question: str, schema_context: str, engine_type: str = "mysql", llm_provider: str = None) -> str:
    """
    Constructs the prompt and calls LLM to generate raw SQL.
    """
    llm = get_llm(provider=llm_provider)
    
    prompt = f"""You are a specialized SQL assistant.
Given the following database schema context, generate a valid {engine_type} SQL query to answer the user's question.

### DATABASE SCHEMA CONTEXT:
{schema_context}

### INSTRUCTIONS:
- Use only the tables and columns provided in the context.
- Return ONLY the raw SQL code. No explanation, no markdowns, no preamble.
- If the question cannot be answered with the current schema, return "ERROR: Schema insufficient".
- Ensure the query is read-only (SELECT only).

### USER QUESTION:
{question}

### SQL QUERY:"""
    
    response = llm.invoke(prompt)
    sql_text = response.content.strip()
    
    # Clean markdown if LLM includes it
    sql_text = sql_text.replace("```sql", "").replace("```", "").strip()
    return sql_text

def execute_query(sql: str, connection_url: str) -> tuple:
    """
    Executes the generated SQL and returns a list of dicts and the SQL used.
    Returns: (sql_used, list_of_dicts, dataframe_or_none)
    """
    engine = create_engine(connection_url)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            # Standardize for JSON response
            data = df.to_dict(orient="records")
            return sql, data, df
    except Exception as e:
        raise Exception(f"SQL execution failed: {str(e)}")

def run_sql_rag_pipeline(question: str, tenant_id: str, db_url: str, db_type: str = "mysql", llm_provider: str = None):
    """
    The full high-level pipeline.
    """
    # 1. Retrieve
    schema_context = retrieve_relevant_schema(question, tenant_id)
    
    # 2. Generate
    sql = generate_sql(question, schema_context, engine_type=db_type, llm_provider=llm_provider)
    
    if sql.startswith("ERROR"):
        return "I don't have enough information about your database to answer that.", None, None
        
    # 3. Execute
    try:
        final_sql, data, df = execute_query(sql, db_url)
        
        # 4. Final Answer formatting (briefly explain the result)
        llm = get_llm(provider=llm_provider)
        summary_prompt = f"The user asked: {question}\nThe SQL used was: {final_sql}\nThe resulting data is: {data[:5]}\n\nPlease provide a very brief summary of these results (1 sentence)."
        summary = llm.invoke(summary_prompt).content
        
        return summary, final_sql, data
    except Exception as e:
        return f"Error executing query: {str(e)}", sql, None
