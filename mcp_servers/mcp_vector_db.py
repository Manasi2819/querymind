"""MCP server exposing ChromaDB similarity search as a tool."""

import asyncio
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp import types
import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../backend"))
from services.embed_service import similarity_search

app = Server("querymind-vector-db")

@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="vector_search",
            description="Search uploaded documents for relevant context using semantic similarity",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "collection": {"type": "string", "default": "default_document"},
                    "k": {"type": "integer", "default": 4},
                },
                "required": ["query"],
            },
        )
    ]

@app.call_tool()
async def call_tool(name: str, arguments: dict) -> list[types.TextContent]:
    if name == "vector_search":
        results = similarity_search(
            arguments["query"],
            arguments.get("collection", "default_document"),
            k=arguments.get("k", 4),
        )
        text = "\n\n".join(r.page_content for r in results)
        return [types.TextContent(type="text", text=text or "No results found.")]
    raise ValueError(f"Unknown tool: {name}")

async def main():
    async with stdio_server() as (read, write):
        await app.run(read, write, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
