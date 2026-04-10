"""
SQL RAG Service — implementation of the Vanna-style "Metadata RAG" pipeline.
Retrieves relevant tables, generates SQL via LLM, and executes the query.
"""

import pandas as pd
from sqlalchemy import create_engine, text
import chromadb
from config import get_settings
from services.llm_service import get_llm, get_embed_model
import re

# SQL Guardrails: Keywords that are forbidden to prevent data modification or schema changes.
FORBIDDEN_SQL_KEYWORDS = [
    "UPDATE", "DELETE", "INSERT", "DROP", "ALTER", "TRUNCATE", 
    "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
]

settings = get_settings()

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

def retrieve_relevant_schema(query: str, tenant_id: str, k: int = 3) -> str:
    """
    Search ChromaDB for the most relevant table/column metadata chunks.
    Prioritizes auto-indexed metadata, but also checks the "Knowledge Base"
    for user-provided schema context (DASHBOARD feature).
    """
    client = get_chroma_client()
    embed_model = get_embed_model()
    query_embedding = embed_model.embed_query(query)
    
    contexts = []
    
    # 1. Primary: Auto-indexed SQL Metadata
    try:
        col_sql = client.get_collection(name=f"{tenant_id}_sql_metadata")
        res_sql = col_sql.query(query_embeddings=[query_embedding], n_results=k)
        if res_sql and res_sql['documents'][0]:
            contexts.extend(res_sql['documents'][0])
    except:
        pass

    # 2. Secondary: User-provided Knowledge Base (SQL, JSON, MD schema info)
    try:
        col_kb = client.get_collection(name=f"{tenant_id}_knowledge_base")
        res_kb = col_kb.query(query_embeddings=[query_embedding], n_results=2)
        if res_kb and res_kb['documents'][0]:
            contexts.append("### EXTENDED USER KNOWLEDGE BASE CONTEXT:")
            contexts.extend(res_kb['documents'][0])
    except:
        pass
    
    if not contexts:
        return "No relevant metadata found. Please configure database or upload knowledge base files."
        
    return "\n\n".join(contexts)

def rewrite_query(question: str, history: str = "", llm_provider: str = None, api_key: str = None, model: str = None) -> str:
    """
    Rewrites the user's question to be self-contained using chat history.
    Example: "What is his email?" -> "What is the email of the CEO of Acme Corp?"
    """
    if not history:
        return question
        
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model)
    prompt = f"""Given the following conversation history and a follow-up question, rewrite the follow-up question to be a standalone, self-contained question for a SQL database.
    If the follow-up question is already self-contained, return it as is.
    Ensure any pronouns (he, she, it, they, their, this, that) are resolved to the original subject.
    Only return the rewritten question text.

    ### CONVERSATION HISTORY:
    {history}

    ### FOLLOW-UP QUESTION:
    {question}

    ### STANDALONE QUESTION:"""
    
    response = llm.invoke(prompt)
    rewritten = response.content.strip()
    return rewritten

def generate_sql(question: str, schema_context: str, engine_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None) -> str:
    """
    Constructs the prompt and calls LLM to generate raw SQL.
    """
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model)
    
    prompt = f"""You are a specialized SQL assistant.
Given the following database schema context, generate a valid {engine_type} SQL query to answer the user's question.

### DATABASE SCHEMA CONTEXT:
{schema_context}

### INSTRUCTIONS:
- Use only the tables and columns provided in the context.
- Return ONLY the raw SQL code. No explanation, no markdowns, no preamble.
- If the question cannot be answered with the current schema, return "ERROR: Schema insufficient".
- Ensure the query is read-only (SELECT only).
- If the user is asking to modify, delete, insert, or change data/schema, do not generate a SELECT to 'show' it; instead, return "ERROR: Forbidden action".

### USER QUESTION:
{question}

### SQL QUERY:"""
    
    response = llm.invoke(prompt)
    sql_text = response.content.strip()
    
    # Clean markdown if LLM includes it
    sql_text = sql_text.replace("```sql", "").replace("```", "").strip()
    return sql_text

def generate_corrected_sql(question: str, schema_context: str, failed_sql: str, error_message: str, engine_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None) -> str:
    """
    Prompts the LLM to fix a broken SQL query based on the error message.
    """
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model)
    
    prompt = f"""You are a specialized SQL assistant.
The previous SQL query you generated failed with an error. Please fix it.

### DATABASE SCHEMA CONTEXT:
{schema_context}

### USER QUESTION:
{question}

### FAILED SQL:
{failed_sql}

### ERROR MESSAGE:
{error_message}

### INSTRUCTIONS:
- Use only the tables and columns provided in the context.
- Return ONLY the corrected raw SQL code. No explanation, no markdowns, no preamble.
- Ensure the query is read-only (SELECT only).
- If the user is asking to modify, delete, insert, or change data/schema, do not generate a SELECT to 'show' it; instead, return "ERROR: Forbidden action".
- Fix the error mentioned in the error message (e.g., syntax, column names, or group by issues).

### CORRECTED SQL QUERY:"""
    
    response = llm.invoke(prompt)
    sql_text = response.content.strip()
    sql_text = sql_text.replace("```sql", "").replace("```", "").strip()
    return sql_text

def validate_sql(sql: str):
    """
    Checks if the SQL query contains any forbidden modification keywords.
    Raises an Exception if a forbidden keyword is found.
    """
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        # Use regex to find the keyword as a whole word to avoid false positives (e.g., 'updated_at' column)
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, sql_upper):
            raise Exception(f"Security Alert: Forbidden SQL keyword '{keyword}' detected. Only SELECT queries are allowed.")

def execute_query(sql: str, connection_url: str) -> tuple:
    """
    Executes the generated SQL and returns a list of dicts and the SQL used.
    Returns: (sql_used, list_of_dicts, dataframe_or_none)
    """
    # 1. Apply hard guardrails before execution
    validate_sql(sql)
    
    from services.database_connection import connect_db
    engine = connect_db(connection_url)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            # Standardize for JSON response
            data = df.to_dict(orient="records")
            return sql, data, df
    except Exception as e:
        raise Exception(f"SQL execution failed: {str(e)}")

def run_sql_rag_pipeline(question: str, tenant_id: str, db_url: str, db_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, history: str = ""):
    """
    The full high-level pipeline with retry logic for SQL correction.
    Now includes query rewriting for context-awareness.
    """
    # 0. Context check & rewrite
    rewritten_question = rewrite_query(question, history, llm_provider, api_key, model)
    
    # 1. Retrieve (Initial)
    schema_context = retrieve_relevant_schema(rewritten_question, tenant_id, k=3)
    
    # 2. Generate (Initial)
    sql = generate_sql(rewritten_question, schema_context, engine_type=db_type, llm_provider=llm_provider, api_key=api_key, model=model)
    
    # Handle initial "Schema insufficient"
    if sql.startswith("ERROR"):
        if "Forbidden action" in sql:
             return "I cannot do that action, I can only fetch data and show it.", None, None
        # USER REQUEST: Try once more by retrieving expanded schema
        schema_context = retrieve_relevant_schema(rewritten_question, tenant_id, k=10)
        sql = generate_sql(rewritten_question, schema_context, engine_type=db_type, llm_provider=llm_provider, api_key=api_key, model=model)
        if sql.startswith("ERROR"):
            return "I don't have enough information about your database to answer that.", None, None
        
    # 3. Execute with Retry Loop
    max_retries = 3
    attempts = 0
    last_error = ""

    while attempts < max_retries:
        try:
            final_sql, data, df = execute_query(sql, db_url)
            
            # 4. Final Answer formatting (Success case)
            llm = get_llm(provider=llm_provider, api_key=api_key, model=model)
            summary_prompt = f"The user asked: {rewritten_question}\nThe SQL used was: {final_sql}\nThe resulting data is: {data[:5]}\n\nPlease provide a very brief summary of these results (1 sentence)."
            summary = llm.invoke(summary_prompt).content
            
            return summary, final_sql, data

        except Exception as e:
            last_error = str(e)
            attempts += 1
            
            if attempts < max_retries:
                # pass the error back to LLM for correction
                sql = generate_corrected_sql(
                    question=rewritten_question,
                    schema_context=schema_context,
                    failed_sql=sql,
                    error_message=last_error,
                    engine_type=db_type,
                    llm_provider=llm_provider,
                    api_key=api_key,
                    model=model
                )
                
                # If LLM reports insufficient schema during correction, try expanded context one last time
                if sql.startswith("ERROR"):
                    schema_context = retrieve_relevant_schema(question, tenant_id, k=10)
                    sql = generate_corrected_sql(
                        question=question,
                        schema_context=schema_context,
                        failed_sql=sql,
                        error_message=last_error,
                        engine_type=db_type,
                        llm_provider=llm_provider,
                        api_key=api_key,
                        model=model
                    )
                    if sql.startswith("ERROR"):
                        break
            else:
                break

    return f"Error executing query after {max_retries} retries: {last_error}", sql, None
