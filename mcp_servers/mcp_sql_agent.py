"""
MCP server wrapping the SQL agent as a tool.
Install: pip install mcp
Run: python mcp_sql_agent.py
"""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))
from services.sql_rag_service import run_sql_rag_pipeline
from routers.admin import get_db_config

app = Server("querymind-sql-agent")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="sql_query",
            description="Convert a natural language question into SQL and execute it against the configured database",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "Natural language question about the data"}
                },
                "required": ["question"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "sql_query":
        # MCP uses default user_1 tenant for global tool mode
        config = get_db_config(user_id=1)
        db_url = config.get("url")
        db_type = config.get("type", "mysql")
        
        if not db_url:
            return [types.TextContent(type="text", text="No database configured in QueryMind. Please connect a DB in the admin panel.")]
        
        summary, sql, data = run_sql_rag_pipeline(
            question=arguments["question"],
            tenant_id="user_1",
            db_url=db_url,
            db_type=db_type
        )
        
        response_text = f"SUMMARY: {summary}\n\nSQL USED:\n```sql\n{sql}\n```\n\nDATA: {data}"
        return [types.TextContent(type="text", text=response_text)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
