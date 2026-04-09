# QueryMind Technical Architecture

## 1. Problem Statement
Many companies struggle with **"Dark Data"**—valuable information trapped inside structured SQL databases or unstructured PDF/Docx files that common employees cannot easily access. Currently:
- **SQL Data** requires knowing complex query syntax (Joins, Aggregations) or waiting for an analyst.
- **Unstructured Knowledge** requires hours of manual searching through policy documents or technical manuals.
- **Security** is a major concern when using public LLMs with sensitive private database connection strings.

## 2. Solution: The QueryMind "Hybrid RAG" Engine
QueryMind solves this by providing a unified, secure, natural-language interface to both data types. It acts as an intelligent middleware that:
1.  **Translates Intent**: Uses an LLM to decide if a question is about "Structured Rows" (SQL) or "Unstructured Context" (Documents).
2.  **Metadata-First SQL RAG**: Unlike simple SQL agents, QueryMind indexes the *metadata* of your tables. This means it only sends the schema context to the LLM, keeping your actual data records private until the query runs locally.
3.  **Cross-Platform LLM Compatibility**: It abstracts provider-specific logic (Ollama, Groq, OpenAI), allowing a single codebase to run anywhere from a private laptop to a high-scale cloud cluster.
4.  **Multi-Tenant Guarding**: Automatically partitions data collections using a `tenant_id` (derived from the JWT), ensuring Vendor A never "sees" Vendor B's database schema or documents.

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
        API_Router[API Routers: Auth, Admin, Chat, Sessions]
        
        %% Core Engines
        SQL_RAG[SQL RAG Engine]
        Doc_RAG[Document RAG Engine]
        Intent[Intent Classifier]
        
        %% State Management
        Auth[JWT Authentication & Security]
        LLM[LLM Gateway / Langchain]
    end

    %% Storage Layer
    subgraph Storage [Persistent Storage]
        MetaDB[(Metadata SQLite DB Model)]
        ChromaStore[(Local ChromaDB Vector Store)]
        UserDB[(Target User Database:\n MySQL/PostgreSQL/SQLite)]
    end

    %% Flow logic
    User -->|Interacts| UI
    User -->|Prompts| Chat
    ExternalClient -->|MCP Protocol| MCPServer
    
    API_Client -->|REST HTTP| API_Router
    MCPServer -->|Internal Call| SQL_RAG
    MCPServer -->|Internal Call| Doc_RAG
    
    API_Router --> Auth
    API_Router --> Intent
    
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
    class API_Router,SQL_RAG,Doc_RAG,Intent,Auth,LLM backend;
    class MetaDB,ChromaStore,UserDB storage;
    class MCPServer mcp;
```

---

## 4. Sub-System Details

### 4.1. Model Context Protocol (MCP) Support
Located in `/mcp_servers`, this allows QueryMind tools to be used by any MCP-compliant client.
- **`mcp_sql_agent.py`**: A standard interface that allows an external AI (like Claude) to "ask" for data from your configured SQL database through QueryMind's secure bridge.
- **`mcp_vector_db.py`**: Allows external agents to search your QueryMind documents for relevant technical context.

### 4.2. Intent Classification Engine
Queries sent to `/chat` are first scrutinized by `services/intent_classifier.py`.
- **Logic**: It uses a few-shot prompting technique to decide if a query is `sql_db` (relational), `knowledge_base` (unstructured), or `general`.
- **Safety**: If the query looks like a destructive SQL command (`DROP`, `DELETE`), it is immediately neutralized.

### 4.3. SQL RAG Pipeline (The "Vanna" Approach)
Implementing a metadata-first RAG:
1.  **MetaData Collection**: Tables and column descriptions are vectorized and stored.
2.  **Schema Contextualization**: On a user question, only relevant table schemas are retrieved.
3.  **SQL Generation & Self-Correction**: If a generated SQL script fails, the error message is fed back into the LLM for up to 3 automated repair attempts.

---

## 5. Deployment & Security
1.  **Database URL Encryption**: Uses Fernet symmetric encryption. Your passwords are never stored in plain text.
2.  **UTC JWT Localized Sessions**: Tokens are signed and verified against timezone-aware durations to prevent "infinite session" exploits.
3.  **Vite Proxy Masking**: The frontend never exposes the backend IP to the client; all calls are routed via a relative proxy to prevent CORS leakage.

