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
from services.sql_agent import run_sql_query
from routers.admin import get_db_url

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
        db_url = get_db_url()
        if not db_url:
            return [types.TextContent(type="text", text="No database configured.")]
        result = run_sql_query(arguments["question"], db_url)
        return [types.TextContent(type="text", text=result)]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
