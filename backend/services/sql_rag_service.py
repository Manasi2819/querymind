"""
SQL RAG Service - implementation of the Vanna-style "Metadata RAG" pipeline.
Retrieves relevant tables, generates SQL via LLM, and executes the query.
"""

import pandas as pd
from sqlalchemy import create_engine, text
import chromadb
import sqlglot
from sqlglot import exp, parse_one
import time
import re
import json
import os
from config import get_settings

# Suppress HuggingFace Hub and Tokenizers warnings
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
from services.llm_service import get_llm, get_embed_model
from services.pipeline_logger import (
    log_rag_retrieval,
    log_query_rewrite,
    log_sql_generation,
    log_sql_validation,
    log_sql_validation_detailed,
    log_table_selection,
    log_sql_execution,
    log_retry_logic,
    log_function_trace,
    log_final_response,
    log_error
)

# SQL Guardrails: Keywords that are forbidden to prevent data modification or schema changes.
FORBIDDEN_SQL_KEYWORDS = [
    "UPDATE", "DELETE", "INSERT", "DROP", "ALTER", "TRUNCATE", 
    "CREATE", "REPLACE", "GRANT", "REVOKE", "EXEC", "EXECUTE"
]

# FORBIDDEN_TABLES: Internal tables that should NEVER be queried by the AI.
FORBIDDEN_TABLES = ["admin_users", "admin_settings", "chat_sessions", "chat_messages", "uploaded_files"]

def _normalize_sql(sql: str) -> str:
    """
    Normalize SQL for semantic duplicate detection.
    Strips extra whitespace and lowercases so near-identical SQL strings
    (same query, different formatting) are correctly identified as duplicates
    in the retry loop, preventing redundant LLM correction attempts.
    """
    return re.sub(r'\s+', ' ', sql.strip()).lower()

settings = get_settings()

def get_chroma_client():
    return chromadb.PersistentClient(path=settings.chroma_persist_dir)

def extract_metadata_from_sql(sql: str) -> dict:
    """
    Extracts table and column names from a SQL query using sqlglot.
    """
    try:
        parsed = parse_one(sql)
        tables = [t.name.lower() for t in parsed.find_all(exp.Table)]
        columns = [c.name.lower() for c in parsed.find_all(exp.Column)]
        return {"tables": list(set(tables)), "columns": list(set(columns))}
    except:
        return {"tables": [], "columns": []}

@log_function_trace
def parse_schema_metadata(schema_text: str) -> dict:
    """
    Parses the combined schema metadata string into a structured dict.
    Mapping: { 
        "tables": { "table_name": ["col1", "col2", ...] },
        "foreign_keys": [ {"from_table": "...", "from_col": "...", "to_table": "...", "to_col": "..."} ]
    }
    """
    schema_map = {"tables": {}, "foreign_keys": []}
    if not schema_text:
        return schema_map
        
    for chunk in schema_text.split("\n\n"):
        table_match = re.search(r"(?i)Table:\s*(\w+)", chunk)
        cols_match = re.search(r"(?i)Columns:\s*(.*)", chunk)
        fks_match = re.search(r"(?i)Foreign Keys:\s*(.*)", chunk)
        
        if table_match and cols_match:
            table_name = table_match.group(1)
            cols_str = cols_match.group(1)
            # Robust splitting: ignore commas inside parentheses (e.g. NUMERIC(18, 2))
            cols_raw = re.split(r",\s*(?![^()]*\))", cols_str)
            # Strip types using greedy match to handle VARCHAR(20)
            # Extract column names and types
            # Format: col1 TYPE1, col2 TYPE2
            cols_with_types = {}
            for c in cols_raw:
                # Match "column_name TYPE" or "column_name (TYPE)"
                # This handles formats like "id INTEGER" or "id (INTEGER)"
                m_col = re.match(r"(\w+)\s+\(?([\w\s,()]+)\)?", c.strip())
                if m_col:
                    cols_with_types[m_col.group(1).lower()] = m_col.group(2).strip()
                else:
                    cols_with_types[c.strip().lower()] = "unknown"
            
            schema_map["tables"][table_name.lower()] = cols_with_types
            
            # Extract Foreign Keys
            if fks_match:
                # Format: ['col'] -> table.['target_col']
                fks_str = fks_match.group(1)
                for fk_entry in fks_str.split(";"):
                    # Regex to match ['from_col'] -> to_table.['to_col']
                    m = re.search(r"\[\'(.+?)\'\]\s*->\s*(.+?)\.\[\'(.+?)\'\]", fk_entry)
                    if m:
                        schema_map["foreign_keys"].append({
                            "from_table": table_name,
                            "from_col": m.group(1),
                            "to_table": m.group(2),
                            "to_col": m.group(3)
                        })
            
    return schema_map

MAX_COLUMNS_PER_TABLE = 10

def get_column_type(table: str, column: str, schema_metadata: dict) -> str:
    """Utility function to get the datatype of a column."""
    tables = schema_metadata.get("tables", {})
    return tables.get(table.lower(), {}).get(column.lower(), "UNKNOWN")

def compress_schema_for_llm(schema_metadata: dict, selected_tables: list = None) -> str:
    """
    Compresses full DDL into minimal JSON structure for token optimization.
    Format: {"table_name": ["col1", "col2", ...]}
    """
    compressed_tables = {}
    tables = schema_metadata.get("tables", {})
    
    for table_name, cols in tables.items():
        if selected_tables and table_name.lower() not in [t.lower() for t in selected_tables]:
            continue
        # Limit to MAX_COLUMNS_PER_TABLE
        compressed_tables[table_name] = list(cols.keys())[:MAX_COLUMNS_PER_TABLE]
        
    # Include foreign keys to prevent hallucinated joins
    fks = schema_metadata.get("foreign_keys", [])
    relevant_fks = []
    for fk in fks:
        if not selected_tables or (fk["from_table"].lower() in [t.lower() for t in selected_tables] and fk["to_table"].lower() in [t.lower() for t in selected_tables]):
            relevant_fks.append(f"{fk['from_table']}.{fk['from_col']} -> {fk['to_table']}.{fk['to_col']}")
            
    output = {
        "tables": compressed_tables,
        "foreign_keys": relevant_fks
    }
    return json.dumps(output, indent=2)

def validate_join_types(sql_query: str, schema_metadata: dict, table_aliases: dict) -> list:
    """
    Extracts JOIN conditions and compares datatypes on both sides.
    Returns structured errors if mismatch found.
    """
    errors = []
    
    def _pg_type_family(type_str: str) -> str:
        t = type_str.upper().strip("() ").split("(")[0].strip()
        if t in ("INTEGER", "INT", "INT4", "INT8", "BIGINT", "SMALLINT", "SERIAL", "BIGSERIAL"): return "integer"
        if t in ("VARCHAR", "CHARACTER VARYING", "TEXT", "CHAR", "BPCHAR", "NAME"): return "text"
        if t in ("NUMERIC", "DECIMAL", "FLOAT", "FLOAT4", "FLOAT8", "REAL", "DOUBLE PRECISION"): return "numeric"
        if t in ("BOOLEAN", "BOOL"): return "boolean"
        if t in ("DATE", "TIMESTAMP", "TIMESTAMPTZ", "TIME"): return "datetime"
        return "other"

    try:
        parsed = parse_one(sql_query, read=None)
        for join in parsed.find_all(exp.Join):
            on_condition = join.args.get("on")
            if on_condition:
                for eq in on_condition.find_all(exp.EQ):
                    left_col = list(eq.left.find_all(exp.Column))
                    right_col = list(eq.right.find_all(exp.Column))
                    
                    if left_col and right_col:
                        # If either side is explicitly cast, assume the LLM fixed the type mismatch
                        if eq.left.find(exp.Cast) or eq.right.find(exp.Cast):
                            continue
                            
                        l_node = left_col[0]
                        r_node = right_col[0]
                        
                        if l_node.table and r_node.table:
                            t1, c1 = l_node.table.lower(), l_node.name.lower()
                            t2, c2 = r_node.table.lower(), r_node.name.lower()
                            
                            real_t1 = table_aliases.get(t1, t1)
                            real_t2 = table_aliases.get(t2, t2)
                            
                            type1 = get_column_type(real_t1, c1, schema_metadata)
                            type2 = get_column_type(real_t2, c2, schema_metadata)
                            
                            fam1 = _pg_type_family(type1)
                            fam2 = _pg_type_family(type2)
                            
                            if type1 == "UNKNOWN" or type2 == "UNKNOWN":
                                continue
                                
                            if fam1 != "other" and fam2 != "other" and fam1 != fam2:
                                errors.append({
                                    "join": f"{real_t1}.{c1} = {real_t2}.{c2}",
                                    "error": f"{type1} != {type2}"
                                })
                            elif (fam1 == "integer" and fam2 == "other") or (fam2 == "integer" and fam1 == "other"):
                                errors.append({
                                    "join": f"{real_t1}.{c1} = {real_t2}.{c2}",
                                    "error": f"{type1} != {type2}"
                                })
    except Exception:
        pass
        
    return errors

@log_function_trace
def validate_sql_against_schema(sql: str, schema_map: dict) -> dict:
    """
    Uses sqlglot to check if tables, columns, and JOINS in the SQL exist in the provided schema_map.
    """
    errors = []
    try:
        # Standardize SQL for parsing
        parsed = parse_one(sql, read=None) # Auto-detect dialect
        
        tables_in_sql = [t.name for t in parsed.find_all(exp.Table)]
        columns_in_sql = [c.name for c in parsed.find_all(exp.Column)]
        
        # Check Tables
        tables_meta = schema_map.get("tables", {})
        schema_map_lower = {k.lower(): [c.lower() for c in v] for k, v in tables_meta.items()}
        
        for table in tables_in_sql:
            if table.lower() not in schema_map_lower:
                errors.append(f"Table '{table}' does not exist in the retrieved schema.")
        
        # 1. Extract Table Mappings (including aliases)
        table_aliases = {}
        for table in parsed.find_all(exp.Table):
            t_name = table.name.lower()
            alias = table.alias.lower() if table.alias else t_name
            table_aliases[alias] = t_name

        # FIX 1: Extract SELECT-clause aliases BEFORE column checking.
        # Aliases like `COUNT(*) AS num_shipments` or `SUM(x) AS total_revenue` are
        # valid SQL constructs used in ORDER BY / GROUP BY. They are NOT physical schema
        # columns and must be whitelisted to prevent false validation failures.
        defined_aliases = set()
        for alias_node in parsed.find_all(exp.Alias):
            if alias_node.alias:
                defined_aliases.add(alias_node.alias.lower())

        # 2. Check Columns
        if not errors:
            for column_node in parsed.find_all(exp.Column):
                col_name = column_node.name.lower()
                col_table_alias = column_node.table.lower() if column_node.table else None
                
                # SKIP validation for '*' and placeholders
                if col_name == "*" or col_name.startswith(":") or col_name.startswith("$") or col_name == "?":
                    continue

                # SKIP validation for SELECT-clause aliases used in ORDER BY / GROUP BY.
                # e.g. ORDER BY num_shipments where num_shipments was defined as
                # COUNT(DISTINCT x) AS num_shipments in the same SELECT clause.
                if col_name in defined_aliases:
                    continue

                if col_table_alias:
                    target_table = table_aliases.get(col_table_alias)
                    if not target_table:
                        errors.append(f"Alias '{col_table_alias}' for column '{col_name}' is not defined.")
                        continue
                    if col_name not in schema_map_lower.get(target_table, []):
                        errors.append(f"Column '{col_name}' does not exist in table '{target_table}'.")
                else:
                    found = False
                    for alias, t_name in table_aliases.items():
                        if col_name in schema_map_lower.get(t_name, []):
                            found = True
                            break
                    if not found:
                        # FIX 4: Include available columns in the error so the LLM
                        # correction prompt has concrete guidance instead of hallucinating.
                        available_cols = []
                        for t in table_aliases.values():
                            available_cols.extend(list(schema_map_lower.get(t, {}).keys()))
                        errors.append(
                            f"Column '{col_name}' not found in any of the queried tables. "
                            f"Available columns in those tables are: {sorted(set(available_cols))}. "
                            f"Do NOT hallucinate columns - use only the listed columns."
                        )

        # FIX 2: Type-aware JOIN validation.
        # Uses validate_join_types to ensure foreign key and primary key datatypes are consistent.
        join_errors = validate_join_types(sql, schema_map, table_aliases)
        for je in join_errors:
            errors.append(f"{je['join']} ({je['error']})")
                    
        return {
            "status": "passed" if not errors else "failed",
            "errors": errors
        }
    except Exception as e:
        return {
            "status": "error",
            "errors": [f"SQL Parsing Error: {str(e)}"]
        }

@log_function_trace
def select_relevant_tables(query: str, schema_text: str, llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> list:
    """
    FIX 3: Table selection now includes dynamic column→table hints built at
    runtime from the actual schema. No hardcoding — hints reflect whichever
    database the user has connected.
    """
    start_time = time.perf_counter()
    
    # Fast-path heuristic
    query_lower = query.lower()
    if "all employees" in query_lower or "all employee" in query_lower:
        return ["employee"]
        
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
    
    # Extract unique table names from schema_text
    table_names = re.findall(r"(?i)Table:\s*(\w+)", schema_text)
    unique_tables = sorted(list(set(table_names)))
    
    if not unique_tables:
        return []

    # FIX 3: Build dynamic column → table mapping from live schema text.
    # This anchors the LLM to the correct table for date/identifier columns
    # that are semantically ambiguous (e.g. "joined" → date_of_joining → employee).
    col_to_table = {}  # col_name -> table_name
    for chunk in schema_text.split("\n\n"):
        tbl_m = re.search(r"(?i)Table:\s*(\w+)", chunk)
        cols_m = re.search(r"(?i)Columns:\s*(.*)", chunk)
        if tbl_m and cols_m:
            tbl = tbl_m.group(1)
            cols_raw = re.split(r",\s*(?![^()]*\))", cols_m.group(1))
            for c in cols_raw:
                cm = re.match(r"(\w+)", c.strip())
                if cm:
                    col_to_table[cm.group(1).lower()] = tbl

    # FIX B: Build a per-table summary (first 5 col names each) instead of a
    # flat col→table map capped at 30.  With 60+ tables the old [:30] cap was
    # non-deterministic and dropped most anchor columns.  Showing every table
    # with its leading columns gives the selector LLM full, stable coverage.
    table_summary_lines = []
    for chunk in schema_text.split("\n\n"):
        tbl_m = re.search(r"(?i)Table:\s*(\w+)", chunk)
        cols_m = re.search(r"(?i)Columns:\s*(.*)", chunk)
        if tbl_m and cols_m:
            tbl = tbl_m.group(1)
            cols_raw = re.split(r",\s*(?![^()]*\))", cols_m.group(1))
            key_cols = []
            for c in cols_raw[:6]:          # first 6 cols are usually the most identifying
                cm = re.match(r"(\w+)", c.strip())
                if cm:
                    key_cols.append(cm.group(1))
            table_summary_lines.append(f"  {tbl}: {', '.join(key_cols)}, ...")
    col_hints_block = "\n".join(table_summary_lines) if table_summary_lines else "  (none)"

    prompt = f"""Given the user question and the available tables, pick the most relevant tables needed to answer the question.
    
    USER QUESTION: {query}
    AVAILABLE TABLES: {', '.join(unique_tables)}
    
    TABLE COLUMN OVERVIEW (table: first few columns):
{col_hints_block}
    
    INSTRUCTIONS:
    - Use the TABLE COLUMN OVERVIEW above to identify which tables contain the columns
      needed to answer the question (e.g. name/ID fields, date fields, status fields).
    - IMPORTANT: If you select a child or history table (e.g. employee_history, employee_address), 
      you MUST ALSO include the main primary table (e.g. employee) to ensure JOINS can be performed.
    - Return ONLY a comma-separated list of table names.
    - Include ALL tables necessary for joins.
    - Limit to 6 tables maximum.
    - If none are relevant, return "NONE".
    
    Example Output: employee, employee_history, master_designation
    """
    
    response = llm.invoke(prompt)
    selected_raw = response.content.strip().upper()
    
    if "NONE" in selected_raw:
        selected = []
    else:
        found_tables = []
        for table in unique_tables:
            if re.search(rf"\b{table}\b", selected_raw, re.IGNORECASE):
                found_tables.append(table.lower())
        selected = found_tables

    duration = (time.perf_counter() - start_time) * 1000
    log_table_selection(selected, query, duration)
    return selected

def retrieve_relevant_schema(query: str, tenant_id: str, k: int = 10, base_url: str = None) -> str:
    """
    FIX 4: Increased default k from 6 → 10 and small-collection threshold
    from 15 → 25 to reduce the chance of missing important tables.
    """
    client = get_chroma_client()
    embed_model = get_embed_model(base_url=base_url)
    query_embedding = embed_model.embed_query(query)
    
    try:
        col_sql = client.get_collection(name=f"{tenant_id}_sql_metadata")
        count = col_sql.count()
        # FIX 4: Raised threshold from 15 → 25 so more databases get full-schema retrieval
        if count <= 25:
            res_sql = col_sql.get()
            if res_sql and res_sql['documents']:
                return "\n\n".join(res_sql['documents'])
        else:
            res_sql = col_sql.query(query_embeddings=[query_embedding], n_results=k)
            if res_sql and res_sql['documents'][0]:
                return "\n\n".join(res_sql['documents'][0])
    except Exception:
        pass
    return "No relevant database schema found."


# FIX A: FK chain expansion helper.
# After the LLM selects tables, we parse FK declarations in raw_schema to
# find any parent/lookup tables that are referenced but not yet selected.
# This guarantees that e.g. selecting 'employee_documents' automatically
# pulls in 'employee' (its FK parent), so the validator never sees a table
# that the schema_map doesn't know about.
_FK_REF_RE = re.compile(r"\['.+?'\]\s*->\s*(\w+)\.\['.+?'\]", re.IGNORECASE)

def expand_tables_via_fk(selected: list, raw_schema: str) -> list:
    """
    Walk FK declarations in raw_schema.  For every selected table that owns
    FK references, add the referenced (parent) table to the selection set.
    Zero hardcoding — works for any database schema.
    """
    expanded = {t.lower() for t in selected}
    # Map table_name → its raw chunk so we can inspect FK lines
    chunk_map = {}
    for chunk in raw_schema.split("\n\n"):
        m = re.search(r"(?i)Table:\s*(\w+)", chunk)
        if m:
            chunk_map[m.group(1).lower()] = chunk

    # Expand: if a selected table has FK → parent, add parent too
    for tbl in list(expanded):          # iterate over a snapshot
        chunk = chunk_map.get(tbl, "")
        for ref_tbl in _FK_REF_RE.findall(chunk):
            expanded.add(ref_tbl.lower())

    return list(expanded)


def retrieve_schema_for_tables(table_names: list, tenant_id: str) -> str:
    """
    Targeted schema retrieval for a specific list of tables.
    Fetches schema docs directly from ChromaDB by metadata — guaranteeing
    the validator always has the exact schema it needs.

    FIX D: Also pull schemas for any tables referenced in FK declarations
    inside the matched docs.  For example, fetching 'employee_documents'
    (which has FK → employee) will automatically include 'employee' so the
    LLM can join correctly and the validator won't reject the query.
    """
    if not table_names:
        return ""
    client = get_chroma_client()
    try:
        col = client.get_collection(name=f"{tenant_id}_sql_metadata")
        all_docs = col.get(include=["documents", "metadatas"])

        lower_targets = {t.lower() for t in table_names}
        matched = []
        matched_tables = set()

        # First pass: fetch docs for the directly requested tables
        for doc, meta in zip(all_docs["documents"], all_docs["metadatas"]):
            tbl = (meta or {}).get("table_name", "").lower()
            if tbl in lower_targets:
                matched.append(doc)
                matched_tables.add(tbl)

        # FIX D: Second pass — collect FK-referenced (parent) tables from
        # the matched docs and pull their schemas too.
        fk_targets = set()
        for doc in matched:
            for ref_tbl in _FK_REF_RE.findall(doc):
                fk_targets.add(ref_tbl.lower())

        # Remove tables we already have
        fk_targets -= matched_tables

        if fk_targets:
            for doc, meta in zip(all_docs["documents"], all_docs["metadatas"]):
                tbl = (meta or {}).get("table_name", "").lower()
                if tbl in fk_targets:
                    matched.append(doc)
                    matched_tables.add(tbl)

        return "\n\n".join(matched)
    except Exception:
        return ""

def retrieve_knowledge_base(query: str, tenant_id: str, k: int = 5, base_url: str = None) -> str:
    client = get_chroma_client()
    embed_model = get_embed_model(base_url=base_url)
    query_embedding = embed_model.embed_query(query)
    
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

@log_function_trace
def rewrite_query(question: str, history: str = "", available_tables: list = None, llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> str:
    if not history:
        return question
        
    start_time = time.perf_counter()
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
    
    table_context = ""
    if available_tables:
        table_context = f"\nAVAILABLE TABLES: {', '.join(available_tables)}\n"

    prompt = f"""Given the following conversation history and a follow-up question, rewrite the follow-up question to be a standalone, self-contained question for a SQL database.
    
    CRITICAL: Replace ALL referential and pronoun words with their explicit referents from the history.
    Referential words to replace: them, those, they, above, these, it, its, this, that, he, him, she, her,
    previous, prior, earlier, former, same, said, such, one, ones, aforementioned.
    
    Example: "how many of them accepted" → "how many of the transporters listed above accepted indents"
    Example: "which of above have joined" → "which of the 13 employees who joined after September 2025 have joined"
    
    {table_context}
    
    STRICT RULES:
    1. Return ONLY the rewritten question text.
    2. Do NOT add any preamble like "Here is the rewritten..." or "Standalone question:".
    3. If the follow-up question is already self-contained with no pronouns, return it as is.
    4. Ensure the output is a single, clear, fully explicit question with no ambiguous references.

    ### CONVERSATION HISTORY:
    {history}

    ### FOLLOW-UP QUESTION:
    {question}

    ### STANDALONE REWRITTEN QUESTION:"""
    
    response = llm.invoke(prompt)
    rewritten = response.content.strip()
    duration = (time.perf_counter() - start_time) * 1000
    log_query_rewrite(question, rewritten, duration)
    return rewritten

def _extract_sql(text: str) -> str:
    match = re.search(r"```(?:sql)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    
    sql = text.strip()
    # Handle common prefixes like "CORRECTED:", "SQL:", "QUERY:", etc.
    preamble_pattern = r"(?i)^.*?(?:here is (the )?query|i have corrected (the )?query|the query is|sql query|corrected|sql|query)[:\s]*"
    sql = re.sub(preamble_pattern, "", sql, count=1).strip()
    sql = re.split(r"(?i)\bnote:|\bexplanation:|\bthis query", sql)[0].strip()
    sql = sql.rstrip(";").strip()
    if sql and not sql.upper().startswith("ERROR") and "SELECT" in sql.upper():
        sql += ";"
    return sql

@log_function_trace
def generate_sql_with_context(question: str, schema: str, knowledge: str, engine_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None, selection_hint: str = "") -> str:
    start_time = time.perf_counter()
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
    
    prompt = f"""You are an expert SQL generator.
    
DATABASE SCHEMA:
{schema}

EXTERNAL KNOWLEDGE:
{knowledge}

USER QUESTION:
{question}

{selection_hint}

INSTRUCTIONS:
- Return ONLY the raw SQL code for {engine_type}. 
- CRITICAL: Do NOT add notes, explanations, or preambles. Just the code.
- Ensure the query is read-only (SELECT only).
- SECURITY: NEVER generate queries for internal tables: {', '.join(FORBIDDEN_TABLES)}.
- LITERAL VALUES: Use actual values from the question in the SQL (e.g., if the user asks for 'IT' department, use WHERE department = 'IT'). 
- NO PLACEHOLDERS: NEVER use placeholders like '?', ':id', or '$1'. Use literal values instead.
- JOIN HINT: In this database, tables usually join on `employee_id` (VARCHAR) or `emp_id` (VARCHAR), NOT the auto-increment primary key `id` (INTEGER). Be careful not to join `employee.id` to `employee_id` in other tables.
- TYPE SAFETY: PostGreSQL is extremely strict. ALWAYS use explicit type casts `CAST(col AS TEXT)` on BOTH sides of EVERY JOIN condition (e.g., `ON CAST(e.employee_id AS TEXT) = CAST(er.employee_id AS TEXT)`). This is mandatory to prevent type mismatch errors.
- HISTORY TABLES: Tables ending in `_history` (e.g. `employee_history`) contain snapshots. They may NOT have the same columns as the main table. Use ONLY the columns listed in the schema for that specific history table. Do NOT assume `created_at` or `modified_at` exist unless listed.
- JOINS: Use the "foreign_keys" section in the schema to determine the correct join columns.
- MINIMAL JOINS: Only join tables if the question explicitly requires data from multiple tables. If the question asks about a single entity (e.g., "all employees"), do NOT join other tables.
- Never invent columns. If a column like 'employee_name' is not listed, use 'first_name || \' \' || last_name' or similar.
- SELECT CLAUSE: If the user asks for "all details", select ONLY the columns explicitly listed in the schema for the tables you are joining. DO NOT invent columns or assign columns to the wrong table alias.
- If column not found → return "ERROR: COLUMN_NOT_FOUND".
- If information is insufficient → return "ERROR: Information insufficient".

### SQL QUERY:"""
    
    response = llm.invoke(prompt)
    sql = _extract_sql(response.content)
    duration = (time.perf_counter() - start_time) * 1000
    log_sql_generation(sql, duration)
    return sql

@log_function_trace
def generate_corrected_sql(question: str, schema_context: str, failed_sql: str, error_message: str, engine_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None) -> str:
    start_time = time.perf_counter()
    llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)

    # Detect PostgreSQL type mismatch error and inject aggressive CAST instruction
    is_type_mismatch = (
        "integer = character varying" in error_message.lower() or
        "undefinedfunction" in error_message.lower() or
        "operator does not exist" in error_message.lower()
    )
    type_mismatch_block = ""
    if is_type_mismatch:
        type_mismatch_block = """
### JOIN ERROR:
The query has JOIN mismatches:
""" + error_message + """
Fix: You MUST fix all failing JOINs by casting to TEXT, e.g. CAST(col1 AS TEXT) = CAST(col2 AS TEXT)
"""

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
{type_mismatch_block}
### INSTRUCTIONS:
- Return ONLY the corrected raw SQL code. 
- CRITICAL: Do NOT add notes, explanations, or preambles. Just the code.
- LITERAL VALUES: Use actual values, NEVER placeholders like '?', ':id', or '$1'.
- TYPE CASTING: If the error contains 'JOIN ERROR', you MUST fix the mentioned columns immediately.
- SCHEMA COMPLIANCE: Use the SCHEMA CONTEXT to find correct column names.
- STRICT COLUMN ADHERENCE: If the error says "Column X does not exist in table Y", you MUST NOT select column X from table Y. Find the correct table that actually contains column X by carefully reading the SCHEMA CONTEXT, or remove the column from the SELECT clause entirely.
- NO HALLUCINATION: Do NOT assume a column exists just because it exists in a related table. History tables often lack metadata columns.
- JOINS: Re-check the "Foreign Keys" section to find the correct relationship.
- COLUMN HALLUCINATION: If 'employee_name' failed, check if you should use `first_name || ' ' || last_name`.

### CORRECTED SQL QUERY:"""
    
    response = llm.invoke(prompt)
    sql = _extract_sql(response.content)
    duration = (time.perf_counter() - start_time) * 1000
    log_sql_generation(f"CORRECTED: {sql}", duration)
    return sql

def validate_sql(sql: str):
    sql_upper = sql.upper()
    for keyword in FORBIDDEN_SQL_KEYWORDS:
        if re.search(rf"\b{keyword}\b", sql_upper):
            raise Exception(f"Security Alert: Forbidden SQL keyword '{keyword}' detected. Only SELECT queries are allowed.")
    for table in FORBIDDEN_TABLES:
        if re.search(rf"\b{table}\b", sql_upper.lower()):
            raise Exception(f"Security Alert: Access to restricted internal table '{table}' is forbidden.")

@log_function_trace
def execute_query(sql: str, connection_url: str) -> tuple:
    """
    Executes the generated SQL and returns a dictionary with columns and rows.
    """
    start_time = time.perf_counter()
    validate_sql(sql)
    
    from services.database_connection import connect_db
    engine = connect_db(connection_url)
    try:
        with engine.connect() as conn:
            df = pd.read_sql(text(sql), conn)
            
            # Optimized format: columns and rows separately
            columns = df.columns.tolist()
            # Handle JSON-safety and datetime conversion
            rows = json.loads(df.to_json(orient="values", date_format="iso"))
            
            data = {"columns": columns, "rows": rows}
            duration = (time.perf_counter() - start_time) * 1000
            log_sql_execution("success", rows_count=len(df), duration_ms=duration)
            return sql, data, df
    except Exception as e:
        duration = (time.perf_counter() - start_time) * 1000
        log_sql_execution("failed", error=str(e), duration_ms=duration)
        raise Exception(f"SQL execution failed: {str(e)}")

@log_function_trace
def run_context_aware_sql_pipeline(question: str, tenant_id: str, db_url: str, db_type: str = "mysql", llm_provider: str = None, api_key: str = None, model: str = None, base_url: str = None, history: str = "", is_related: bool = False):
    """
    Stage-Aware SQL RAG Pipeline.

    Stages:
    1. Schema RAG Retrieval
    2. Schema-Aware Query Rewriting (if related)
    3. Table Selection (soft filtering)
    4. SQL Generation
    5. Smart Retry Loop (Validate → Execute only - NO summary inside loop)
    6. Stage-Aware Summary Generation (OUTSIDE loop):
       - total_rows > 50 → deterministic bypass (no LLM call)
       - total_rows <= 50 → LLM summary with 1 dedicated retry
       - 413 / repeated failure → graceful fallback message
    """
    start_pipeline_time = time.perf_counter()

    # ── Stage 1: Schema Retrieval ────────────────────────────────────────────
    raw_schema = retrieve_relevant_schema(question, tenant_id, k=6, base_url=base_url)
    log_rag_retrieval(6, "schema", 0)

    available_tables = re.findall(r"(?i)Table:\s*(\w+)", raw_schema)
    available_tables = sorted(list(set(available_tables)))

    # ── Stage 2: Query Rewriting ──────────────────────────────────────────────
    rewritten_question = question
    if history and is_related:
        rewritten_question = rewrite_query(
            question, history, available_tables, llm_provider, api_key, model, base_url
        )

    # ── Stage 3: Table Selection (Soft Filtering) ────────────────────────────
    selected_tables = select_relevant_tables(
        rewritten_question, raw_schema, llm_provider, api_key, model, base_url
    )

    # FIX A: Expand selected_tables by following FK chains in raw_schema.
    # If 'employee_documents' is selected and it has FK → employee, then
    # 'employee' is automatically added so the schema_map never misses it.
    selected_tables = expand_tables_via_fk(selected_tables, raw_schema)

    # Fetch schema DIRECTLY for the (now FK-expanded) selected tables.
    # This is a targeted lookup by table name — independent of embedding search.
    targeted_schema = retrieve_schema_for_tables(selected_tables, tenant_id)
    # retrieve_schema_for_tables already follows FK refs (Fix D), so
    # targeted_schema now includes parent table schemas automatically.

    # Merge: start with the targeted docs, then append any extra context from
    # the RAG results that wasn't already included. This preserves full JOIN
    # context while guaranteeing selected-table coverage.
    if targeted_schema:
        targeted_tables_found = set(re.findall(r"(?i)Table:\s*(\w+)", targeted_schema))
        extra_chunks = []
        for chunk in raw_schema.split("\n\n"):
            m = re.search(r"(?i)Table:\s*(\w+)", chunk)
            if m and m.group(1).lower() not in {t.lower() for t in targeted_tables_found}:
                extra_chunks.append(chunk)
        schema_context = targeted_schema + ("\n\n" + "\n\n".join(extra_chunks) if extra_chunks else "")
    else:
        schema_context = raw_schema  # fallback: use RAG schema as-is

    # FIX E: Pre-flight FK coverage check.
    # Parse the assembled schema_context and verify that every table appearing
    # as an FK target actually has its schema present.  If any are missing,
    # fetch and append them now — before SQL generation, not after failure.
    schema_map_preflight = parse_schema_metadata(schema_context)
    known_tables = set(schema_map_preflight["tables"].keys())
    fk_targets_needed = {
        fk["to_table"].lower()
        for fk in schema_map_preflight.get("foreign_keys", [])
    }
    missing_fk_tables = fk_targets_needed - known_tables
    if missing_fk_tables:
        patch = retrieve_schema_for_tables(list(missing_fk_tables), tenant_id)
        if patch:
            schema_context += "\n\n" + patch

    selection_hint = ""
    if selected_tables:
        selection_hint = f"PRIMARY TABLES TO FOCUS ON: {', '.join(selected_tables)}"

    knowledge = retrieve_knowledge_base(rewritten_question, tenant_id, k=5, base_url=base_url)
    log_rag_retrieval(5, "knowledge", 0)

    # ── Stage 4: SQL Generation ───────────────────────────────────────────────
    # Token Optimization: compress schema_context before passing to LLM
    compressed_schema = compress_schema_for_llm(schema_map_preflight, selected_tables)

    sql = generate_sql_with_context(
        question=rewritten_question,
        schema=compressed_schema,
        knowledge=knowledge,
        engine_type=db_type,
        llm_provider=llm_provider,
        api_key=api_key,
        model=model,
        base_url=base_url,
        selection_hint=selection_hint,
    )

    if sql.startswith("ERROR"):
        if "Forbidden action" in sql:
            return "I cannot do that action, I can only fetch data and show it.", None, None, None
        if "COLUMN_NOT_FOUND" in sql:
            return "I couldn't find the necessary columns to answer this question.", sql, None, None
        return "I don't have enough information to generate a correct SQL query.", None, None, None

    # ── Stage 5: Smart Retry Loop (Validate + Execute ONLY) ──────────────────
    # NOTE: Summary generation is intentionally OUTSIDE this loop.
    # A summary failure must never restart the SQL/DB pipeline.
    max_retries = 3
    attempts = 0
    last_error = ""
    previous_sqls = []
    df = None
    data = None
    final_sql = None
    schema_map = parse_schema_metadata(schema_context)

    while attempts < max_retries:
        val_res = validate_sql_against_schema(sql, schema_map)
        log_sql_validation_detailed(sql, val_res["status"], val_res["errors"])

        if val_res["status"] != "passed":
            # For validation errors, we capture all errors and don't execute
            error_msg = "\n".join(val_res["errors"])
            if " != " in error_msg:
                error_msg = f"JOIN ERROR:\n{error_msg}"
            else:
                error_msg = f"Schema Validation Error:\n{error_msg}"

            # FIX C: Self-healing schema injection on "Table X does not exist".
            # When the validator reports a missing table, fetch that table's
            # schema from ChromaDB and append it to schema_context + reparse
            # schema_map BEFORE the correction LLM call.  This means the
            # correction prompt gets the full schema, and the validator will
            # pass on the very next attempt — no more 3-retry death spirals.
            missing_in_err = re.findall(
                r"Table '(\w+)' does not exist in the retrieved schema",
                error_msg
            )
            if missing_in_err:
                patch = retrieve_schema_for_tables(missing_in_err, tenant_id)
                if patch:
                    schema_context += "\n\n" + patch
                    schema_map = parse_schema_metadata(schema_context)  # reparse with new tables
        else:
            try:
                final_sql, data, df = execute_query(sql, db_url)
                break  # ── SUCCESS: exit retry loop ────────────────────────
            except Exception as e:
                error_msg = str(e)

        last_error = error_msg
        previous_sqls.append(sql)
        attempts += 1
        log_retry_logic(attempts, last_error, sql)

        if attempts < max_retries:
            combined_context = f"SCHEMA:\n{compressed_schema}\n\nKNOWLEDGE:\n{knowledge}"
            sql = generate_corrected_sql(
                question=rewritten_question,
                schema_context=combined_context,
                failed_sql=sql,
                error_message=last_error,
                engine_type=db_type,
                llm_provider=llm_provider,
                api_key=api_key,
                model=model,
                base_url=base_url,
            )
            # Semantic deduplication — normalize before comparing so that
            # near-identical SQL (same logic, different whitespace/formatting)
            # is correctly detected as a duplicate and skips a redundant retry.
            if _normalize_sql(sql) in [_normalize_sql(s) for s in previous_sqls]:
                break
            if sql.startswith("ERROR"):
                break
        else:
            break

    # ── Check if SQL execution succeeded ─────────────────────────────────────
    if df is None:
        duration_total = (time.perf_counter() - start_pipeline_time) * 1000
        log_final_response("failed", duration_total)
        return "The pipeline encountered a recurring error that it couldn't fix automatically.", None, None, None

    total_rows = len(df)
    total_cols = len(df.columns)

    # ── Stage 6: Stage-Aware Summary Generation ───────────────────────────────
    # DETERMINISTIC BYPASS: If the query returned more than 50 rows, we skip
    # the LLM summary entirely. This means: no LLM call is made, so no 413
    # "Request too large" error can occur, and the response is instant.
    # The full dataset is still returned to the UI for display as a table.
    if total_rows > 50:
        summary = f"Found {total_rows} records matching your query. Displaying results in table format."
    else:
        # Build compact payload - max 20 rows to stay within token limits
        if total_rows <= 20:
            sample_data = data["rows"]
            sample_info = f"Showing all {total_rows} rows."
        else:
            sample_data = data["rows"][:20]
            sample_info = f"Showing a sample of the first 20 out of {total_rows} total rows."

        summary_prompt = f"""
        The user asked: {rewritten_question}
        SQL used: {final_sql}

        RESULT METADATA:
        - Total Rows: {total_rows}
        - Total Columns: {total_cols}
        - Data Content: {sample_info}

        DATA SAMPLES (Values only):
        {sample_data}

        COLUMNS:
        {data['columns']}

        INSTRUCTIONS:
        Provide a brief (2-3 sentences) natural language summary of these results.
        - IMPORTANT: You MUST reference the total number of records ({total_rows}) in your summary.
        - CRITICAL: Include the names or primary identifiers of the first 3-5 results so the user can ask follow-up questions.
        - If there are many rows, summarize the overall findings and list the top few.
        - SECURITY: NEVER mention API keys, passwords, or database secrets in this summary.
        - Keep the tone helpful and concise.
        """

        summary = None
        for summary_attempt in range(2):  # 1 main attempt + 1 dedicated retry
            try:
                llm = get_llm(provider=llm_provider, api_key=api_key, model=model, base_url=base_url)
                summary = llm.invoke(summary_prompt).content.strip()
                break  # Success
            except Exception as sum_err:
                err_str = str(sum_err)
                log_error("SUMMARY_GEN", f"Summary attempt {summary_attempt + 1} failed: {err_str[:120]}")
                # 413 is a permanent error - do NOT retry, return fallback immediately
                if "413" in err_str or "too large" in err_str.lower():
                    break
                # Other errors get 1 retry (transient network issues, etc.)

        if summary is None:
            summary = f"Found {total_rows} records matching your query."

    duration_total = (time.perf_counter() - start_pipeline_time) * 1000
    log_final_response("success", duration_total)

    execution_metadata = extract_metadata_from_sql(final_sql)
    execution_metadata["topic"] = summary[:100]
    execution_metadata["summary"] = summary

    return summary, final_sql, data, execution_metadata
