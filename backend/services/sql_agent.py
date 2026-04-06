"""
SQL Agent — converts natural language to SQL and executes it.
Uses LangChain's create_sql_agent with the user-configured DB.
"""

from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import create_sql_agent
from langchain.agents import AgentType
from services.llm_service import get_llm

import re

def build_sql_agent(db_url: str, llm_provider: str = None, api_key: str = None):
    """Builds a SQL agent for the given database URL."""
    db = SQLDatabase.from_uri(db_url)
    
    # ── GUARDRAIL: Block non-read-only commands ──
    original_run = db.run
    def guardrail_run(command: str, fetch: str = "all"):
        # Remove comments and strings, then check for forbidden DML/DDL keywords
        cmd_no_comments = re.sub(r'--.*$', '', command, flags=re.MULTILINE)
        cmd_no_comments = re.sub(r'/\*.*?\*/', '', cmd_no_comments, flags=re.DOTALL)
        cmd_no_strings = re.sub(r"'.*?'", '', cmd_no_comments)
        cmd_no_strings = re.sub(r'".*?"', '', cmd_no_strings)
        
        forbidden = r'\b(insert|update|delete|drop|alter|create|truncate|replace|grant|revoke|commit|rollback)\b'
        if re.search(forbidden, cmd_no_strings, re.IGNORECASE):
            return "Error: Execution blocked. Only read-only (SELECT) queries are allowed."
            
        return original_run(command, fetch)
        
    db.run = guardrail_run
    # ─────────────────────────────────────────────

    llm = get_llm(provider=llm_provider, api_key=api_key)
    agent = create_sql_agent(
        llm=llm,
        db=db,
        agent_type=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
        verbose=False,
        handle_parsing_errors=True,
    )
    return agent

def run_sql_query(question: str, db_url: str, llm_provider: str = None, api_key: str = None) -> str:
    """Runs a natural language question against the configured SQL database."""
    try:
        agent = build_sql_agent(db_url, llm_provider, api_key)
        result = agent.invoke({"input": question})
        return result.get("output", "No result returned.")
    except Exception as e:
        return f"SQL agent error: {str(e)}"

def test_connection(db_url: str) -> dict:
    """Tests whether the DB connection is valid."""
    try:
        db = SQLDatabase.from_uri(db_url)
        tables = db.get_usable_table_names()
        return {"success": True, "tables": tables}
    except Exception as e:
        return {"success": False, "error": str(e)}
