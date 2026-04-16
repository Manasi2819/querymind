# QueryMind Technical Architecture

## 1. Problem Statement
Many companies struggle with **"Dark Data"**—valuable information trapped inside structured SQL databases or unstructured PDF/Docx files that common employees cannot easily access. Currently:
- **SQL Data** requires knowing complex query syntax (Joins, Aggregations) or waiting for an analyst.
- **Unstructured Knowledge** requires hours of manual searching through policy documents or technical manuals.
- **Security** is a major concern when using public LLMs with sensitive private database connections or proprietary documents.

## 2. Solution: The QueryMind "Hybrid RAG" Engine
QueryMind provides a unified, secure, natural-language interface to both structured and unstructured data. It acts as an intelligent middleware that:
1.  **Translates Intent**: Uses a specialized LLM-based classifier to decide if a question is about "Structured Rows" (SQL) or "Unstructured Context" (Documents).
2.  **Metadata-First SQL RAG**: Unlike simple SQL agents, QueryMind indexes only the *metadata* (schemas, table descriptions) of your database. Actual data records remain local and private.
3.  **Cross-Platform Adapter**: Abstracts provider-specific logic (Ollama, Groq, OpenAI), allowing the system to run on anything from a laptop to a cloud cluster.
4.  **Security-First Design**: Implements hardcoded DML guardrails and per-tenant data partitioning using IDs derived from secure JWT tokens.

---

## 3. Core System Architecture

```mermaid
graph TD
    %% Define users
    User([Standard Admin/Vendor User]) 
    ExternalClient([External MCP Client:\ne.g. Claude Desktop])

    %% Frontend Services
    subgraph Frontend [React / Vite Frontend (Port 5173)]
        UI[Dashboard & Settings Interface]
        Chat[Chatbot Conversation UI]
        Widget[Embeddable JS Widget]
        UI --> API_Client[Axios API Client]
        Chat --> API_Client
    end

    %% MCP Layer
    subgraph MCP [MCP Tool Layer]
        MCPServer[MCP Servers:\nSQL & Vector Agents]
    end

    %% Backend Services
    subgraph Backend [FastAPI Backend (Port 8000)]
        API_Router[API Router: /chat]
        Guard[SQL Guardrails:\nDML Keywords Check]
        
        %% Core Engines
        Intent[Intent Classifier:\nLLM + Keyword Fallback]
        SQL_RAG[SQL RAG Engine:\nRewriting -> Schema RAG -> SQL Gen]
        Doc_RAG[Document RAG Engine:\nMulti-Collection Vector Search]
        
        %% State Management
        Auth[JWT Auth & Tenant Isolation]
        LLM[LLM Gateway / Langchain]
    end

    %% Storage Layer
    subgraph Storage [Persistent Storage]
        MetaDB[(App SQLite DB:\nHistory & Config)]
        ChromaStore[(Local ChromaDB Vector Store)]
        UserDB[(Target User Database:\n MySQL/Postgres/SQLite)]
    end

    %% Flow logic
    User -->|Interacts| UI
    User -->|Prompts| Chat
    ExternalClient -->|MCP Protocol| MCPServer
    
    API_Client -->|REST HTTP| API_Router
    MCPServer -->|Internal Call| SQL_RAG
    MCPServer -->|Internal Call| Doc_RAG
    
    API_Router --> Auth
    Auth --> Guard
    Guard --> Intent
    
    Intent -->|SQL Route| SQL_RAG
    Intent -->|Doc Route| Doc_RAG
    
    SQL_RAG --> UserDB
    Doc_RAG --> ChromaStore
    
    SQL_RAG --> LLM
    Doc_RAG --> LLM
    LLM --> API_Router
    API_Router --> MetaDB

    %% Styling
    classDef frontend fill:#3b82f6,stroke:#1d4ed8,stroke-width:2px,color:white;
    classDef backend fill:#10b981,stroke:#047857,stroke-width:2px,color:white;
    classDef storage fill:#f59e0b,stroke:#b45309,stroke-width:2px,color:white;
    classDef mcp fill:#8b5cf6,stroke:#7c3aed,stroke-width:2px,color:white;
    
    class UI,Chat,Widget,API_Client frontend;
    class API_Router,Guard,SQL_RAG,Doc_RAG,Intent,Auth,LLM backend;
    class MetaDB,ChromaStore,UserDB storage;
    class MCPServer mcp;
```

---

## 4. Sub-System Details

### 4.1. Intent Classification Engine
Queries sent to `/chat` are first prioritized by `services/intent_classifier.py`.
- **Logic**: It uses a few-shot prompting technique to decide if a query is `sql_with_context` (relational), `rag` (unstructured), `unauthorized` (DML attempts), or `chat` (general).
- **Smart Routing**: Passes context (history, DB/Doc status) to the LLM for precise routing.
- **Keyword Fallback**: If the LLM fails, a robust keyword matcher ensures the query is still routed correctly based on detected intent patterns.

### 4.2. SQL RAG Pipeline (Metadata-First)
QueryMind uses a specialized Vanna-inspired pipeline in `services/sql_rag_service.py`:
1.  **Query Rewriting**: Refactors follow-up questions into standalone queries using chat history (resolving pronouns).
2.  **Context Assembly**: Retrieves relevant table schemas and "External Knowledge" (data dictionary chunks) from ChromaDB.
3.  **SQL Generation**: Assembles a context-aware prompt to generate read-only SQL for the target engine (MySQL/PostgreSQL/SQLite).
4.  **Self-Correction Loop**: If execution fails, the system feeds the error back to the LLM for up to 3 automated repair attempts.

### 4.3. Document RAG Pipeline
Handled by `services/rag_service.py`, this pipeline provides context from unstructured data:
- **Multi-Collection Search**: Searches across `general_document`, `knowledge_base`, and `data_dictionary` collections simultaneously.
- **Context-Aware Answering**: Generates answers strictly from retrieved context, avoiding hallucinations by instructing the LLM to only use "ground truth" data.

### 4.4. Model Context Protocol (MCP) Support
Located in `/mcp_servers`, this allows QueryMind tools to be used by any MCP-compliant client (e.g., Claude Desktop).
- **`mcp_sql_agent.py`**: A secure bridge allowing external agents to query configured SQL databases.
- **`mcp_vector_db.py`**: Allows external agents to search ingested documents for technical context.

---

## 5. Security & Isolation
1.  **DML Protection**: Hardcoded `FORBIDDEN_SQL_KEYWORDS` (DROP, DELETE, UPDATE) are blocked at the router level *before* reaching the LLM.
2.  **Tenant Isolation**: All Vector Store collections and SQL metadata are prefixed with a `tenant_id` (e.g., `user_1_sql_metadata`), ensuring strict data partitioning at the storage layer.
3.  **Encryption**: Uses `Fernet` symmetric encryption for sensitive Database URLs. Credentials are never stored in plain text.
4.  **Token-Based Auth**: Secure JWT sessions map users to their respective isolated data environments.

