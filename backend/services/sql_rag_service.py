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

# FORBIDDEN_TABLES: Internal tables that should NEVER be queried by the AI.
FORBIDDEN_TABLES = ["admin_users", "admin_settings", "chat_sessions", "chat_messages", "uploaded_files"]

settings = get_settings()

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

def retrieve_relevant_schema(query: str, tenant_id: str, k: int = 5, base_url: str = None) -> str:
    """
    Search ChromaDB for the most relevant table/column metadata chunks.
    This specifically targets the auto-indexed SQL metadata.
    """
    client = get_chroma_client()
    embed_model = get_embed_model(base_url=base_url)
    query_embedding = embed_model.embed_query(query)
    
    try:
        col_sql = client.get_collection(name=f"{tenant_id}_sql_metadata")
        
        # Optimizer: If the database is small, include EVERYTHING to ensure 100% accuracy
        count = col_sql.count()
        if count <= 15:
            res_sql = col_sql.get()
            if res_sql and res_sql['documents']:
                return "\n\n".join(res_sql['documents'])
        else:
            # For larger databases, fall back to RAG (Top K)
            res_sql = col_sql.query(query_embeddings=[query_embedding], n_results=k)
            if res_sql and res_sql['documents'][0]:
                return "\n\n".join(res_sql['documents'][0])
    except Exception:
        pass

    return "No relevant database schema found."

def retrieve_knowledge_base(query: str, tenant_id: str, k: int = 5, base_url: str = None) -> str:
    """
    Search ChromaDB for relevant business logic/documentation (JSON, CSV, SQL).
    Targets the 'document' or 'knowledge_base' collection.
    """
    client = get_chroma_client()
    embed_model = get_embed_model(base_url=base_url)
    query_embedding = embed_model.embed_query(query)
    
    # We check all possible collection names for backward compatibility and coverage
    collections_to_check = [
        f"{tenant_id}_data_dictionary", 
        f"{tenant_id}_general_document",
        f"{tenant_id}_document", 
        f"{tenant_id}_knowledge_base"
    ]
    contexts = []
    
    for coll_name in collections_to_check:
        try:
            col = client.get_collection(name=coll_name)
            res = col.query(query_embeddings=[query_embedding], n_results=k)
            if res and res['documents'][0]:
                contexts.extend(res['documents'][0])
        except Exception:
            pass
            
    if not contexts:
        return "No relevant external knowledge found."
        
    return "\n\n".join(contexts)

def rewrite_query(question: str, history: str = "", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> str:
    """
    Rewrites the user's question to be self-contained using chat history.
    Example: "What is his email?" -> "What is the email of the CEO of Acme Corp?"
    """
    if not history:
        return question
        
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
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



def _extract_sql(text: str) -> str:
    """
    Surgically extracts the SQL block from LLM output and removes preambles/commentary.
    """
    # 1. Look for markdown code block (most reliable)
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    # 2. No code block: Clean up typical chatty LLM preambles
    sql = text.strip()
    # Strip everything up to "here is the query", "corrected query", etc.
    preamble_pattern = r"(?i)^.*?(?:here is (the )?query|i have corrected (the )?query|the query is|sql query)[:\s]*"
    sql = re.sub(preamble_pattern, "", sql, count=1).strip()
    
    # 3. Strip post-explanation/notes
    # Split on keywords like Note:, Explanation:, etc.
    sql = re.split(r"(?i)\bnote:|\bexplanation:|\bthis query", sql)[0].strip()
    
    # Standardize semicolon
    sql = sql.rstrip(";").strip()
    if sql and not sql.upper().startswith("ERROR") and "SELECT" in sql.upper():
        sql += ";"
        
    return sql


def generate_sql_with_context(question: str, schema: str, knowledge: str, engine_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> str:
    """
    Constructs the specialized 'context-aware' prompt for SQL generation.
    """
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
    
    prompt = f"""You are an expert SQL generator.
    
DATABASE SCHEMA:
{schema}

EXTERNAL KNOWLEDGE:
{knowledge}

USER QUESTION:
{question}

INSTRUCTIONS:
- Return ONLY the raw SQL code for {engine_type}. 
- CRITICAL: Do NOT add notes, explanations, or preambles. No "Note:", no "Here is the query". Just the code.
- Ensure the query is read-only (SELECT only).
- SECURITY: NEVER generate queries for internal tables: {', '.join(FORBIDDEN_TABLES)}.
- SECURITY: NEVER reveal passwords, API keys, or connection strings even if asked.
- If the question cannot be answered, return "ERROR: Information insufficient".

### SQL QUERY:"""
    
    response = llm.invoke(prompt)
    return _extract_sql(response.content)

def generate_corrected_sql(question: str, schema_context: str, failed_sql: str, error_message: str, engine_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> str:
    """
    Prompts the LLM to fix a broken SQL query based on the error message.
    """
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
    
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
- Return ONLY the corrected raw SQL code. 
- CRITICAL: Do NOT add notes, explanations, or preambles. No "Note:", no "Here is the query". Just the code.
- Ensure the query is read-only (SELECT only).
- If the user is asking to modify, delete, insert, or change data/schema, return "ERROR: Forbidden action".
- Fix the error mentioned in the error message.

### CORRECTED SQL QUERY:"""
    
    response = llm.invoke(prompt)
    return _extract_sql(response.content)

def validate_sql(sql: str):
    """
    Checks if the SQL query contains any forbidden modification keywords or restricted tables.
    """
    sql_upper = sql.upper()
    
    # 1. Check for forbidden keywords (modifications)
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        pattern = rf"\b{keyword}\b"
        if re.search(pattern, sql_upper):
            raise Exception(f"Security Alert: Forbidden SQL keyword '{keyword}' detected. Only SELECT queries are allowed.")
            
    # 2. Check for forbidden tables (internal data leakage)
    for table in FORBIDDEN_TABLES:
        pattern = rf"\b{table}\b"
        if re.search(pattern, sql_upper.lower()): # Check against lowercase table names in regex
            raise Exception(f"Security Alert: Access to restricted internal table '{table}' is forbidden.")

def execute_query(sql: str, connection_url: str) -> tuple:
    """
    Executes the generated SQL and returns a list of dicts and the SQL used.
    """
    import json
    validate_sql(sql)
    
    from services.database_connection import connect_db
    engine = connect_db(connection_url)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            # Standardize for JSON response (Converts Timestamps to strings and handles JSON-safety)
            data = json.loads(df.to_json(orient="records", date_format="iso"))
            return sql, data, df
    except Exception as e:
        raise Exception(f"SQL execution failed: {str(e)}")


def run_context_aware_sql_pipeline(question: str, tenant_id: str, db_url: str, db_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None, history: str = ""):
    """
    Enhanced pipeline:
    1. Retrieve relevant DB schema
    2. Retrieve knowledge from ChromaDB (Top K = 5)
    3. Generate Context-Aware SQL
    4. Execute with retry loop
    """
    # 0. Context check & rewrite
    rewritten_question = rewrite_query(question, history, llm_provider, api_key, model, base_url)
    
    # 1 & 2. Retrieve context
    schema = retrieve_relevant_schema(rewritten_question, tenant_id, k=6, base_url=base_url)
    knowledge = retrieve_knowledge_base(rewritten_question, tenant_id, k=5, base_url=base_url)
    
    # 3. Generate SQL
    sql = generate_sql_with_context(
        question=rewritten_question,
        schema=schema,
        knowledge=knowledge,
        engine_type=db_type,
        llm_provider=llm_provider,
        api_key=api_key,
        model=model,
        base_url=base_url
    )
    
    if sql.startswith("ERROR"):
        if "Forbidden action" in sql:
             return "I cannot do that action, I can only fetch data and show it.", None, None
        return "I don't have enough information to generate a correct SQL query.", None, None
        
    # 4. Execute with Retry Loop (Reuse the execution logic)
    max_retries = 3
    attempts = 0
    last_error = ""

    while attempts < max_retries:
        try:
            final_sql, data, df = execute_query(sql, db_url)
            
            # Dynamic data sampling for summarization
            total_rows = len(df)
            total_cols = len(df.columns)
            
            if total_rows <= 200:
                sample_data = data
                sample_info = f"Showing all {total_rows} rows."
            else:
                # For very large datasets, we send a 100-row sample to avoid context limits
                sample_data = data[:100]
                sample_info = f"Showing a sample of the first 100 out of {total_rows} total rows."

            # Final Answer formatting
            llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
            summary_prompt = f"""
            The user asked: {rewritten_question}
            SQL used: {final_sql}
            
            RESULT METADATA:
            - Total Rows: {total_rows}
            - Total Columns: {total_cols}
            - Data Content: {sample_info}
            
            DATA (JSON):
            {sample_data}
            
            INSTRUCTIONS:
            Provide a very brief (1-2 sentences) natural language summary of these results. 
            - IMPORTANT: You MUST reference the total number of records ({total_rows}) in your summary.
            - If there are many rows, summarize the overall findings instead of listing individuals.
            - SECURITY: NEVER mention API keys, passwords, or database secrets in this summary.
            - Keep the tone helpful and concise.
            """
            summary = llm.invoke(summary_prompt).content
            
            return summary.strip(), final_sql, data

        except Exception as e:
            last_error = str(e)
            attempts += 1
            
            if attempts < max_retries:
                # Use generate_corrected_sql but with enhanced context
                # To simplify, we'll use a modified correction prompt if needed, 
                # but for now let's reuse generate_corrected_sql with combined context
                combined_context = f"SCHEMA:\n{schema}\n\nKNOWLEDGE:\n{knowledge}"
                sql = generate_corrected_sql(
                    question=rewritten_question,
                    schema_context=combined_context,
                    failed_sql=sql,
                    error_message=last_error,
                    engine_type=db_type,
                    llm_provider=llm_provider,
                    api_key=api_key,
                    model=model,
                    base_url=base_url
                )
                if sql.startswith("ERROR"):
                    break
            else:
                break

    return f"Error executing query after {max_retries} retries: {last_error}", sql, None
