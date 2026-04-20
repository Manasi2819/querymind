# QueryMind — Technical Architecture

**Version**: 2.0 (Production-Ready)  
**Last Updated**: April 2026

---

## 1. Problem Statement

Many organizations struggle with **"Dark Data"** — valuable information trapped in:
- **Structured SQL databases** requiring complex query syntax (JOINs, aggregations) only accessible to analysts.
- **Unstructured knowledge** buried in PDFs, DOCX files, and internal wikis.
- **Security risks** from exposing sensitive production databases to public LLM APIs.

---

## 2. Solution: The QueryMind Hybrid RAG Engine

QueryMind provides a secure, unified, natural-language interface to both structured and unstructured data. It acts as an intelligent middleware layer that:

1. **Translates Intent** — Uses an LLM-based classifier to route each question to the correct data pipeline (SQL, Document RAG, or general chat).
2. **Metadata-First SQL RAG** — Indexes only database *schemas* (table names, column types, AI-generated descriptions) into ChromaDB — raw data never leaves the user's database.
3. **Multi-Provider LLM Abstraction** — A single `get_llm()` factory supports 5 providers (Ollama, OpenAI, Anthropic, Gemini, Groq) with automatic model migration for decommissioned versions.
4. **Security-First by Design** — Layered DML guardrails, Fernet encryption at rest, DLP output redaction, and JWT tenant isolation.

---

## 3. Core System Architecture

```mermaid
graph TD
    %% Clients
    User([Admin / End User])
    ExtAgent([External MCP Client\ne.g. Claude Desktop])

    %% Frontend
    subgraph Frontend ["React / Vite Frontend  ·  Port 5173 (Dev) / Nginx (Docker)"]
        LoginPage[Login Page]
        Dashboard[Dashboard]
        ChatUI[Chat Interface]
        DBConfig[Database Config]
        KBPage[Knowledge Base]
        LLMPage[LLM Settings]
        AxiosClient[Axios API Client\nsrc/api/client.js]

        LoginPage --> AxiosClient
        Dashboard --> AxiosClient
        ChatUI --> AxiosClient
        DBConfig --> AxiosClient
        KBPage --> AxiosClient
        LLMPage --> AxiosClient
    end

    %% MCP Layer
    subgraph MCP ["MCP Tool Layer  ·  mcp_servers/"]
        MCPSql[mcp_sql_agent.py\nSQL Query Tool]
        MCPVec[mcp_vector_db.py\nVector Search Tool]
    end

    %% Backend
    subgraph Backend ["FastAPI Backend  ·  Port 8000"]
        Router_Chat[POST /chat]
        Router_Admin[/admin/* routes]
        Router_Sessions[/sessions/* routes]

        Guard[Pre-LLM SQL Guard\nDML Keyword Regex Block]
        Intent[Intent Classifier\nLLM + Keyword Fallback]

        subgraph Pipelines ["Core Pipelines"]
            SQL_RAG[SQL RAG Pipeline\nsql_rag_service.py]
            Doc_RAG[Document RAG Pipeline\nrag_service.py]
            Redactor[DLP Redaction\nredaction_service.py]
        end

        subgraph Services ["Shared Services"]
            LLMSvc[LLM Gateway\nllm_service.py]
            EmbedSvc[Embed Service\nembed_service.py]
            EncSvc[Encryption Service\nencryption.py]
            DBConnSvc[DB Connection\ndatabase_connection.py]
            MetaSvc[SQL Metadata Indexer\nsql_metadata_service.py]
            IngestSvc[Ingest Pipeline\ningest_service.py]
        end

        Auth[JWT Auth\nauth.py]
        Config[Settings\nconfig.py / .env]
    end

    %% Storage
    subgraph Storage ["Persistent Storage"]
        AppDB[(App Database\nSQLite / MySQL / PostgreSQL\nUsers, Sessions, Config)]
        ChromaDB[(ChromaDB\nVector Store\nDoc chunks + SQL metadata)]
        UserDB[(User's Target Database\nMySQL / PostgreSQL / SQLite)]
        UploadDir[/uploads/\nRaw uploaded files]
    end

    %% LLM Providers
    subgraph LLMProviders ["LLM Providers"]
        Ollama[Ollama\nLocal / self-hosted]
        OpenAI[OpenAI\nGPT-4o-mini etc.]
        Anthropic[Anthropic\nClaude 3.5 Haiku]
        Gemini[Google Gemini\nGemini Flash]
        Groq[Groq\nLlama 3.3 70B]
    end

    %% Flow
    User --> Frontend
    ExtAgent -->|MCP Protocol| MCP

    AxiosClient -->|HTTPS REST| Router_Chat
    AxiosClient -->|HTTPS REST| Router_Admin
    AxiosClient -->|HTTPS REST| Router_Sessions

    MCPSql -->|Direct Python call| SQL_RAG
    MCPVec -->|Direct Python call| Doc_RAG

    Router_Chat --> Auth
    Router_Admin --> Auth
    Auth --> Guard
    Guard --> Intent

    Intent -->|sql_with_context| SQL_RAG
    Intent -->|rag| Doc_RAG
    Intent -->|unauthorized| Redactor
    Intent -->|chat| Redactor

    SQL_RAG --> DBConnSvc --> UserDB
    SQL_RAG --> EmbedSvc --> ChromaDB
    SQL_RAG --> LLMSvc

    Doc_RAG --> EmbedSvc
    Doc_RAG --> LLMSvc

    LLMSvc --> Ollama & OpenAI & Anthropic & Gemini & Groq

    Router_Admin --> IngestSvc --> EmbedSvc
    Router_Admin --> MetaSvc --> ChromaDB
    Router_Admin --> EncSvc
    Router_Admin --> DBConnSvc

    Redactor -->|Sanitized response| Router_Chat
    Router_Chat --> AppDB

    Config -.->|env vars| LLMSvc & Auth & AppDB

    classDef frontend fill:#3b82f6,stroke:#1d4ed8,color:white
    classDef backend fill:#10b981,stroke:#047857,color:white
    classDef storage fill:#f59e0b,stroke:#b45309,color:white
    classDef mcp fill:#8b5cf6,stroke:#7c3aed,color:white
    classDef llm fill:#ef4444,stroke:#b91c1c,color:white

    class LoginPage,Dashboard,ChatUI,DBConfig,KBPage,LLMPage,AxiosClient frontend
    class Router_Chat,Router_Admin,Router_Sessions,Guard,Intent,SQL_RAG,Doc_RAG,Redactor,LLMSvc,EmbedSvc,EncSvc,DBConnSvc,MetaSvc,IngestSvc,Auth,Config backend
    class AppDB,ChromaDB,UserDB,UploadDir storage
    class MCPSql,MCPVec mcp
    class Ollama,OpenAI,Anthropic,Gemini,Groq llm
```

---

## 4. Request Lifecycle — Chat Flow

A single chat message follows this path:

```
POST /chat
  │
  ├─ 1. JWT Token Validation (auth.py)
  │
  ├─ 2. Pre-LLM SQL Guard
  │      └─ Regex blocks DML keywords (DROP, DELETE, etc.) before LLM call
  │
  ├─ 3. Load User Context
  │      ├─ LLM config (provider, model, encrypted API key) — decrypted
  │      └─ DB config (encrypted connection URL) — decrypted
  │
  ├─ 4. Intent Classification (intent_classifier.py)
  │      ├─ LLM-based: prompt → 'sql_with_context' | 'rag' | 'unauthorized' | 'chat'
  │      └─ Keyword fallback if LLM errors
  │
  ├─ 5a. SQL Route → run_context_aware_sql_pipeline()
  │        ├─ Query Rewriting (resolves pronouns from history)
  │        ├─ Schema RAG (ChromaDB: {tenant}_sql_metadata collection)
  │        ├─ Knowledge RAG (ChromaDB: {tenant}_data_dictionary, etc.)
  │        ├─ SQL Generation (context-aware prompt → LLM)
  │        ├─ SQL Validation (FORBIDDEN_SQL_KEYWORDS + FORBIDDEN_TABLES)
  │        ├─ SQL Execution (SQLAlchemy → user's DB)
  │        └─ Self-Correction Loop (up to 3 retries on failure)
  │
  ├─ 5b. RAG Route → answer_from_docs()
  │        ├─ Multi-collection vector search (all tenant collections)
  │        └─ Context-grounded LLM answer generation
  │
  ├─ 6. DLP Redaction (redaction_service.py)
  │      └─ Scans output for API keys, passwords, DB URLs → [REDACTED]
  │
  └─ 7. Persist to AppDB + Return ChatResponse
```

---

## 5. Sub-System Details

### 5.1. LLM Factory (`services/llm_service.py`)

The central LLM gateway used by every other service:

- **Priority**: Explicit args > per-user DB config > `.env` defaults
- **Model Migration**: Automatically remaps decommissioned model names (e.g., `mixtral-8x7b-32768` → `llama-3.3-70b-versatile`)
- **Lazy Imports**: Provider-specific packages are imported inside branches to avoid `ImportError` when a provider isn't installed

Supported providers and their defaults:

| Provider | Default Model | Config Field |
|---|---|---|
| `ollama` | `llama3.2` | `OLLAMA_MODEL` |
| `openai` | `gpt-4o-mini` | `OPENAI_MODEL` |
| `anthropic` | `claude-3-5-haiku-20241022` | `ANTHROPIC_MODEL` |
| `gemini` | `gemini-1.5-flash` | `GEMINI_MODEL` |
| `groq` | `llama3-8b-8192` | `GROQ_MODEL` |

### 5.2. SQL RAG Pipeline (`services/sql_rag_service.py`)

A Vanna-inspired, context-aware generation pipeline:

| Step | Function | Description |
|---|---|---|
| 1 | `rewrite_query()` | Resolves ambiguous pronouns using chat history |
| 2 | `retrieve_relevant_schema()` | Fetches top-K schema chunks from `{tenant}_sql_metadata` |
| 3 | `retrieve_knowledge_base()` | Fetches top-K business logic from data dictionary collections |
| 4 | `generate_sql_with_context()` | Assembles context-rich prompt → LLM → raw SQL |
| 5 | `_extract_sql()` | Surgically extracts SQL from markdown code blocks |
| 6 | `validate_sql()` | Blocks forbidden keywords and internal table access |
| 7 | `execute_query()` | SQLAlchemy execute → pandas DataFrame → JSON |
| 8 | Retry Loop | On error, calls `generate_corrected_sql()` with the error message (max 3 attempts) |

**Smart Optimizer**: For databases with ≤ 15 schema chunks, the full schema is sent directly (bypassing vector search) for maximum accuracy.

### 5.3. Schema Indexing Pipeline (`services/sql_metadata_service.py`)

Triggered automatically when a user connects a database:

1. `SQLAlchemy.inspect()` → extract all table names, column types, PKs, FKs
2. `generate_table_interpretation()` → LLM generates a 1-sentence natural language description per table
3. Formatted chunks stored in ChromaDB (`{tenant}_sql_metadata`) with Ollama `nomic-embed-text` embeddings

### 5.4. Document RAG Pipeline (`services/rag_service.py`)

Multi-collection vector search for unstructured knowledge:

- Searches all tenant collections simultaneously: `{tenant}_general_document`, `{tenant}_data_dictionary`, `{tenant}_document`, `{tenant}_knowledge_base`
- Deduplicates collection names; limits to top 6 documents per query
- LLM is strictly instructed to answer only from retrieved context (no hallucination)

### 5.5. Intent Classifier (`services/intent_classifier.py`)

Two-layer routing:

| Layer | Mechanism | Output |
|---|---|---|
| Primary | LLM few-shot prompt with full context (history, DB/doc availability) | `sql_with_context` / `rag` / `unauthorized` / `chat` |
| Fallback | Keyword list matching (SQL terms, doc terms, forbidden terms) | Same 4 categories |

Infrastructure-aware: if DB is not configured, `sql_with_context` falls back to `rag`; if neither is configured, falls back to `chat`.

### 5.6. Encryption Service (`services/encryption.py`)

- **Algorithm**: Fernet symmetric encryption (AES-128-CBC + HMAC)
- **Key**: `FERNET_KEY` env var (base64-encoded 32-byte key)
- **Applied to**: DB connection URLs, LLM API keys in `admin_settings`
- **Backward compatibility**: Decryption silently falls back to plaintext for legacy unencrypted data

### 5.7. DLP Redaction (`services/redaction_service.py`)

Applied to **every LLM response** before returning to the client:

| Pattern | Action |
|---|---|
| `sk-[a-zA-Z0-9]{32,}` (OpenAI keys) | → `[REDACTED_API_KEY]` |
| `gsk_[a-zA-Z0-9]{32,}` (Groq keys) | → `[REDACTED_GROQ_KEY]` |
| `mysql://user:password@host` (DB URLs) | Password portion → `********` |
| `key/password/secret/token = value` | Value → `********` |

---

## 6. Data Storage Architecture

| Data Type | Storage | Location |
|---|---|---|
| User accounts | SQL table | `admin_users` |
| Per-user LLM + DB config | JSON column (encrypted) | `admin_settings.llm_config`, `.db_config` |
| Chat sessions | SQL table | `chat_sessions` |
| Chat messages + SQL + results | SQL table + JSON column | `chat_messages` |
| Uploaded file metadata | SQL table | `uploaded_files` |
| Document embeddings | ChromaDB | `{tenant}_general_document`, `{tenant}_data_dictionary` |
| SQL schema embeddings | ChromaDB | `{tenant}_sql_metadata` |
| Raw uploaded files | Filesystem | `backend/uploads/` |

*Full data flow details: see [`docs/DATA_ARCHITECTURE.md`](./docs/DATA_ARCHITECTURE.md)*

---

## 7. Docker Deployment Architecture

The `docker-compose.yml` orchestrates **7 services**:

| Service | Image | Port | Role |
|---|---|---|---|
| `backend` | Custom (FastAPI) | 8000 | Python API server |
| `frontend` | Custom (React + Nginx) | 5173 | Static React app served via Nginx |
| `mysql` | `mysql:8.0` | 3306 | Application metadata database |
| `redis` | `redis:7-alpine` | 6379 | Session caching layer |
| `chromadb` | `chromadb/chroma` | 8001 | Vector store server |
| `ollama` | `ollama/ollama` | 11434 | Local LLM inference server |
| `init` | Custom helper | — | Seeds DB and pulls Ollama models on startup |

**Startup sequence** (via healthchecks): `mysql` → `chromadb` → `backend` → `frontend`

**Data persistence** (via named volumes): `mysql_data`, `chroma_data`, `ollama_data`, `redis_data`, `uploads_data`

---

## 8. Security Model

### 8.1. Layered Defense

```
Request → [JWT Auth] → [Pre-LLM DML Guard] → [Intent Classifier] → [Pipeline] → [DLP Redactor] → Response
```

No single layer is responsible for all security — each acts as a separate failsafe.

### 8.2. SQL Security Controls

1. **Pre-LLM Guard** (`routers/chat.py`): Regex blocks `DROP`, `DELETE`, `UPDATE`, `INSERT`, etc. *before* any LLM call
2. **Prompt Guardrails** (`sql_rag_service.py`): System prompt explicitly forbids DML in SQL generation
3. **Post-Generation Validation** (`validate_sql()`): Double-checks the generated SQL against the forbidden keyword list
4. **Internal Table Blocklist**: `admin_users`, `admin_settings`, `chat_sessions`, `chat_messages`, `uploaded_files` are forbidden in SQL WHERE/FROM clauses
5. **Read-Only Execution**: SQLAlchemy `pd.read_sql()` always used; INSERT/UPDATE/DELETE never called

### 8.3. Tenant Isolation

All ChromaDB collections are namespaced: `user_{id}_sql_metadata`, `user_{id}_general_document`, etc.  
User settings are scoped via `AdminSettings.user_id` with FK constraints.

---

## 9. Configuration Reference

All configuration is managed via `backend/config.py` (Pydantic Settings) and read from `.env`:

```env
# LLM
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama3.2
OLLAMA_EMBED_MODEL=nomic-embed-text
OPENAI_API_KEY=
ANTHROPIC_API_KEY=
GEMINI_API_KEY=
GROQ_API_KEY=

# App Database (SQLAlchemy URL)
DATABASE_URL=sqlite:///./querymind_metadata.db

# Redis
REDIS_URL=redis://localhost:6379/0

# Auth & Encryption
JWT_SECRET_KEY=           # REQUIRED
JWT_ALGORITHM=HS256
JWT_EXPIRE_MINUTES=1440
FERNET_KEY=               # REQUIRED

# Storage
CHROMA_PERSIST_DIR=../chroma_db
UPLOAD_DIR=./uploads

# Admin defaults (seeded on first startup)
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```
