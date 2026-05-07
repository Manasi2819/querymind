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
import time
from core.logger import pipeline_logger

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
                docs = res_sql['documents'][0]
                pipeline_logger.info("RAG Schema Retrieval", extra={"stage": "RAG_RETRIEVAL", "payload": {"query": query, "num_docs": len(docs), "collection": f"{tenant_id}_sql_metadata"}})
                return "\n\n".join(docs)
    except Exception as e:
        pipeline_logger.warning("RAG Schema Retrieval Failed", extra={"stage": "RAG_RETRIEVAL", "payload": {"error": str(e)}})
        pass

    pipeline_logger.info("RAG Schema Retrieval", extra={"stage": "RAG_RETRIEVAL", "payload": {"query": query, "num_docs": 0}})
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
            
    pipeline_logger.info("RAG Knowledge Retrieval", extra={"stage": "RAG_RETRIEVAL", "payload": {"query": query, "num_docs": len(contexts)}})
            
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
    
    classification = "fresh_query" if not history else ("follow-up" if rewritten != question else "contextual_query")
    pipeline_logger.info(
        "Query Rewrite Output", 
        extra={
            "stage": "QUERY_REWRITE", 
            "payload": {
                "original": question, 
                "rewritten": rewritten, 
                "classification": classification,
                "used_context": bool(history)
            }
        }
    )
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


def _extract_bad_identifier(error_message: str) -> str | None:
    """
    Parses a psycopg2 / SQLAlchemy error message and returns the specific
    column or table name that does not exist so it can be banned in the
    retry prompt.

    Examples handled:
      - "column e.employee_name does not exist"  ->  "employee_name"
      - 'relation "employee_profile" does not exist'  ->  "employee_profile"
    """
    # Column pattern: 'column <alias.>name does not exist'
    col_match = re.search(r'column [\w.]*?(\w+) does not exist', error_message, re.IGNORECASE)
    if col_match:
        return col_match.group(1)

    # Table / relation pattern: 'relation "name" does not exist'
    rel_match = re.search(r'relation "([^"]+)" does not exist', error_message, re.IGNORECASE)
    if rel_match:
        return rel_match.group(1)

    return None


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

def generate_corrected_sql(
    question: str,
    schema_context: str,
    failed_sql: str,
    error_message: str,
    available_tables: list = None,
    engine_type: str = "mysql",
    llm_provider: str = None,
    api_key: str = None,
    model: str = None,
    base_url: str = None
) -> str:
    """
    Prompts the LLM to fix a broken SQL query based on the error message.
    Injects:
      - A definitive list of ALL available tables (so the LLM cannot invent ones)
      - A BANNED identifier section (so the LLM cannot reuse the failing name)
      - A strict CRITICAL instruction forbidding name-guessing
    """
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)

    # --- Build the AVAILABLE TABLES block ---
    if available_tables:
        tables_line = ", ".join(available_tables)
        available_tables_block = f"### AVAILABLE TABLES (ONLY these tables exist — do NOT use any other):\n{tables_line}"
    else:
        available_tables_block = ""

    # --- Build the BANNED identifier block ---
    bad_id = _extract_bad_identifier(error_message)
    if bad_id:
        banned_block = (
            f"### BANNED IDENTIFIER:\n"
            f"Do NOT use `{bad_id}` — it does not exist in the database. "
            f"Using it again will cause the same error."
        )
    else:
        banned_block = ""

    prompt = f"""You are a specialized SQL assistant.
The previous SQL query you generated failed with an error. Please fix it.

{available_tables_block}

### DATABASE SCHEMA CONTEXT:
{schema_context}

{banned_block}

### USER QUESTION:
{question}

### FAILED SQL:
{failed_sql}

### ERROR MESSAGE:
{error_message}

### INSTRUCTIONS:
- Return ONLY the corrected raw SQL code.
- CRITICAL: Do NOT add notes, explanations, or preambles. No "Note:", no "Here is the query". Just the code.
- CRITICAL: You must ONLY use the columns and tables listed under AVAILABLE TABLES and SCHEMA CONTEXT.
  If a column is missing, do NOT guess its name; instead, look for the closest real match in the
  provided schema (e.g., use `first_name` + `last_name` instead of `name`).
- Ensure the query is read-only (SELECT only).
- If the user is asking to modify, delete, insert, or change data/schema, return "ERROR: Forbidden action".

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
            pipeline_logger.warning("SQL Validation Failed", extra={"stage": "SQL_VALIDATION", "payload": {"status": "failed", "reason": f"Forbidden keyword: {keyword}"}})
            raise Exception(f"Security Alert: Forbidden SQL keyword '{keyword}' detected. Only SELECT queries are allowed.")
            
    # 2. Check for forbidden tables (internal data leakage)
    for table in FORBIDDEN_TABLES:
        pattern = rf"\b{table}\b"
        if re.search(pattern, sql_upper.lower()): # Check against lowercase table names in regex
            pipeline_logger.warning("SQL Validation Failed", extra={"stage": "SQL_VALIDATION", "payload": {"status": "failed", "reason": f"Forbidden table: {table}"}})
            raise Exception(f"Security Alert: Access to restricted internal table '{table}' is forbidden.")
            
    pipeline_logger.info("SQL Validation Passed", extra={"stage": "SQL_VALIDATION", "payload": {"status": "passed"}})

def execute_query(sql: str, connection_url: str) -> tuple:
    """
    Executes the generated SQL and returns a list of dicts and the SQL used.
    """
    import json
    validate_sql(sql)
    
    from services.database_connection import connect_db
    engine = connect_db(connection_url)
    try:
        start_time = time.time()
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            # Standardize for JSON response (Converts Timestamps to strings and handles JSON-safety)
            data = json.loads(df.to_json(orient="records", date_format="iso"))
            exec_time = round(time.time() - start_time, 3)
            pipeline_logger.info("SQL Execution Success", extra={"stage": "SQL_EXECUTION", "payload": {"execution_time_sec": exec_time, "returned_rows": len(df)}})
            return sql, data, df
    except Exception as e:
        pipeline_logger.error("SQL Execution Failed", extra={"stage": "SQL_EXECUTION", "payload": {"error": str(e)}})
        raise Exception(f"SQL execution failed: {str(e)}")


def run_context_aware_sql_pipeline(question: str, tenant_id: str, db_url: str, db_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None, history: str = "", is_related: bool = True):
    """
    Enhanced pipeline:
    1. Retrieve relevant DB schema
    2. Retrieve knowledge from ChromaDB (Top K = 5)
    3. Generate Context-Aware SQL
    4. Execute with retry loop
    """
    pipeline_logger.info("Pipeline Started", extra={"stage": "USER_INPUT", "payload": {"question": question, "tenant_id": tenant_id}})

    # 0. Context check & rewrite
    if is_related and history:
        rewritten_question = rewrite_query(question, history, llm_provider, api_key, model, base_url)
    else:
        # For fresh queries, we use the original question directly
        rewritten_question = question
        pipeline_logger.info("Query Rewrite Skipped", extra={"stage": "QUERY_REWRITE", "payload": {"reason": "fresh_query" if not is_related else "no_history"}})
    
    # 1 & 2. Retrieve context
    schema = retrieve_relevant_schema(rewritten_question, tenant_id, k=6, base_url=base_url)
    knowledge = retrieve_knowledge_base(rewritten_question, tenant_id, k=5, base_url=base_url)
    
    # 5. Schema Validation Log (Lightweight context dump before LLM)
    schema_snippet = schema[:500] + "..." if len(schema) > 500 else schema
    pipeline_logger.info("Schema Context Selected", extra={"stage": "SCHEMA_LOGGING", "payload": {"schema_snippet": schema_snippet}})
    
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
    
    pipeline_logger.info("SQL Generated", extra={"stage": "SQL_GENERATION", "payload": {"generated_sql": sql}})
    
    if sql.startswith("ERROR"):
        if "Forbidden action" in sql:
             return "I cannot do that action, I can only fetch data and show it.", None, None
        return "I don't have enough information to generate a correct SQL query.", None, None
        
    # 4. Execute with Retry Loop — ONLY retries on SQL execution errors.
    #    Summary generation happens OUTSIDE this loop to avoid misclassifying
    #    a token-limit (413) error on the summary as a SQL failure.
    max_retries = 3
    attempts = 0
    last_error = ""
    final_sql = None
    data = None
    df = None

    while attempts < max_retries:
        try:
            final_sql, data, df = execute_query(sql, db_url)
            # SQL succeeded — break out of retry loop
            break

        except Exception as e:
            last_error = str(e)
            attempts += 1

            if attempts < max_retries:
                combined_context = f"SCHEMA:\n{schema}\n\nKNOWLEDGE:\n{knowledge}"

                # Fetch all real table names from the DB so the LLM cannot invent tables
                all_db_tables = []
                try:
                    from sqlalchemy import inspect as sa_inspect
                    from services.database_connection import connect_db
                    _engine = connect_db(db_url)
                    all_db_tables = sa_inspect(_engine).get_table_names()
                except Exception:
                    pass  # Non-fatal: prompt will still contain schema context

                pipeline_logger.info(
                    "Triggering Retry",
                    extra={"stage": "RETRY_LOGIC", "payload": {
                        "attempt": attempts,
                        "reason": last_error,
                        "failed_sql": sql,
                        "available_tables": all_db_tables
                    }}
                )

                sql = generate_corrected_sql(
                    question=rewritten_question,
                    schema_context=combined_context,
                    failed_sql=sql,
                    error_message=last_error,
                    available_tables=all_db_tables,
                    engine_type=db_type,
                    llm_provider=llm_provider,
                    api_key=api_key,
                    model=model,
                    base_url=base_url
                )
                pipeline_logger.info("Corrected SQL Generated", extra={"stage": "RETRY_LOGIC", "payload": {"attempt": attempts, "corrected_sql": sql}})
                if sql.startswith("ERROR"):
                    break
            else:
                break

    # If all retries exhausted without a successful execution, fail here.
    if df is None:
        pipeline_logger.error("Pipeline Failed", extra={"stage": "FINAL_RESPONSE", "payload": {"status": "failed", "error": last_error}})
        return f"Error executing query after {max_retries} retries: {last_error}", sql, None

    # 5. Summarise — runs AFTER the retry loop so a 413/timeout here never
    #    causes needless SQL regeneration.
    total_rows = len(df)
    total_cols = len(df.columns)

    # Send at most 5 rows to the summary LLM to stay well within token limits.
    # The full dataset is still returned to the frontend via `data`.
    SUMMARY_SAMPLE_SIZE = 5
    if total_rows <= SUMMARY_SAMPLE_SIZE:
        sample_data = data
        sample_info = f"Showing all {total_rows} rows."
    else:
        sample_data = data[:SUMMARY_SAMPLE_SIZE]
        sample_info = f"Showing {SUMMARY_SAMPLE_SIZE} representative rows out of {total_rows} total rows."

    try:
        llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
        summary_prompt = f"""The user asked: {rewritten_question}
SQL used: {final_sql}

RESULT METADATA:
- Total Rows: {total_rows}
- Total Columns: {total_cols}
- {sample_info}

SAMPLE DATA (JSON):
{sample_data}

INSTRUCTIONS:
Provide a very brief (1-2 sentences) natural language summary of these results.
- IMPORTANT: You MUST reference the total number of records ({total_rows}) in your summary.
- If there are many rows, summarize the overall findings instead of listing individuals.
- SECURITY: NEVER mention API keys, passwords, or database secrets.
- Keep the tone helpful and concise."""

        summary = llm.invoke(summary_prompt).content.strip()
    except Exception as summary_err:
        # Graceful fallback — the query data is still returned even if summarisation fails.
        summary = f"Query returned {total_rows} row(s) across {total_cols} column(s)."
        pipeline_logger.warning("Summary Generation Failed", extra={"stage": "SUMMARISATION", "payload": {"error": str(summary_err), "fallback_used": True}})

    pipeline_logger.info("Pipeline Completed", extra={"stage": "FINAL_RESPONSE", "payload": {"status": "success", "final_sql": final_sql, "summary": summary}})
    return summary, final_sql, data
