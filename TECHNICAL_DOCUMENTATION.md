# QueryMind — Technical Documentation

**Version**: 3.0 (Optimized Deployment)  
**Last Updated**: April 2026

---

## 1. System Architecture

QueryMind is built as a modular application designed for high security and resource efficiency. It consists of a React-based frontend and a FastAPI backend, both served from a single Docker container.

### 1.1. Component Stack
- **Frontend**: React (Vite) - Handles session management, chat UI, and administrative configurations.
- **Backend**: FastAPI (Python) - Provides asynchronous API endpoints for chat, ingestion, and management.
- **Database (Metadata)**: SQLite - Stores user accounts, sessions, message history, and encrypted configurations.
- **Vector Database**: ChromaDB - Stores document embeddings and SQL schema descriptions for retrieval.
- **AI Engine**: LangChain-powered RAG (Retrieval-Augmented Generation).

---

## 2. RAG Pipeline Flow

The core of QueryMind is its ability to route queries to the appropriate knowledge source.

### 2.1. Intent Classification
Every query is first processed by the `IntentClassifier`:
- **SQL Route**: If the query relates to structured data (e.g., "how many users...").
- **Document RAG Route**: If the query relates to knowledge in uploaded files (e.g., "what is our policy on...").
- **General Chat**: For basic greetings or general questions.

### 2.2. Document RAG Workflow
1. **Retrieval**: ChromaDB is queried for top-K relevant text chunks using `nomic-embed-text` embeddings.
2. **Context Assembly**: Chunks are combined with conversation history.
3. **Generation**: An LLM prompt is constructed with the context and query.
4. **Validation**: The response is scanned for sensitive data (DLP) before delivery.

---

## 3. Deployment Architecture

QueryMind uses a **Multi-Stage Docker Build** to minimize image size and maximize security.

### 3.1. Build Stages
1. **Stage 1 (Frontend Build)**: Compiles React source into a `dist/` folder using Node.js.
2. **Stage 2 (Dependency Builder)**: Compiles Python wheels (including CPU-only PyTorch) in a throwaway environment with build tools.
3. **Stage 3 (Final Runtime)**: 
   - Uses a clean `python:3.11-slim` base.
   - Installs pre-compiled wheels (no build tools in production).
   - Copies the frontend `dist/` into `backend/static/`.
   - Result: A single ~1.2GB image (optimized from >3GB) that serves both UI and API.

### 3.2. Hosting
Optimized for deployment on an **Azure VM** (e.g., B2s or B4ms instances) using Docker Compose. Persistent data is handled via Docker Named Volumes:
- `querymind_data`: SQLite metadata.
- `querymind_chroma`: Vector database.
- `querymind_uploads`: Raw document storage.

---

## 4. Authentication Flow

QueryMind uses a standard JWT-based authentication system:
1. **Login**: Admin submits credentials to `/admin/token`.
2. **Verification**: Backend verifies hash against SQLite `admin_users` table.
3. **JWT Issuance**: A signed token is returned (stored in the browser's `localStorage`).
4. **Authorized Requests**: All `/admin/*` routes require the `Authorization: Bearer <token>` header.

---

## 5. Database Schema (SQLite)

| Table | Purpose |
|---|---|
| `admin_users` | Stores administrator credentials (username, password hash). |
| `admin_settings` | Stores per-user encrypted LLM configs and Database connection strings. |
| `uploaded_files` | Metadata for document files (filename, upload date, chunk count). |
| `chat_sessions` | Groups chat messages into conversational sessions. |
| `chat_messages` | Stores individual messages, roles (user/assistant), and RAG sources. |

---

## 6. API Documentation Summary

### Authentication
- `POST /admin/token`: Exchange credentials for a JWT token.

### Chat & Sessions
- `POST /chat`: Primary RAG interface for queries.
- `GET /sessions`: Retrieve conversational history.
- `DELETE /sessions/{id}`: Clean up chat history.

### Document Management
- `POST /admin/upload`: Ingest documents (PDF, DOCX, CSV) into the vector store.
- `GET /admin/files`: List all indexed files.

### Configuration
- `POST /admin/llm-config`: Set the LLM provider and API keys (encrypted).
- `POST /admin/db-config`: Connect external SQL databases for querying.

---

## 7. Integration Architecture

QueryMind is designed to be easily integrated into existing enterprise ecosystems via multiple interfaces.

### 7.1. Pluggable Chat Widget
- **Technology**: Vanilla HTML5/JS (Framework-agnostic).
- **Usage**: Embeddable in any web portal (CRM, ERP, Intranet).
- **Customization**: Simple configuration for `API_URL` and `TENANT_ID`.

### 7.2. Standardized REST API
- **Protocol**: OpenAPI (Swagger) compliant.
- **Flexibility**: Can be used by mobile applications, custom frontends, or backend microservices.
- **Statelessness**: Uses JWT for authorization, making it easy to scale behind load balancers.

### 7.3. MCP (Model Context Protocol) Support
- **Components**: `mcp_sql_agent.py` and `mcp_vector_db.py`.
- **Purpose**: Allows external AI agents (like Claude Desktop) to leverage QueryMind's SQL and document search tools as native capabilities.

### 7.4. Native Database Connectors
- **Dialects**: Built-in support for MySQL, PostgreSQL, and SQLite.
- **Workflow**: Point QueryMind at an existing database; it automatically indexes the schema and enables natural language querying without code changes.

---

### 7.1. Security Layers
- **SQL Guard**: Regex-based blocking of DML keywords (DROP, DELETE, etc.) before they reach the LLM.
- **Fernet Encryption**: Sensitive keys and DB strings are encrypted at rest in SQLite.
- **DLP Redaction**: Automated scanning of LLM outputs to redact potential secrets (API keys, passwords).

### 7.2. Error Handling
- **Graceful Fallback**: If the LLM or Vector store is unavailable, the system provides clear "unavailable" messages rather than crashing.
- **SQL Self-Correction**: The SQL RAG pipeline attempts to fix generated queries up to 3 times if an error is returned from the database engine.
