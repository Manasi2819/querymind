# 🧠 QueryMind — Enterprise SQL & Document Chatbot

QueryMind is a production-ready, RAG-enabled AI chatbot that bridges natural language and enterprise data. Query SQL databases (MySQL, PostgreSQL, SQLite) and internal documents using any major LLM provider — powered by Ollama (local), OpenAI, Anthropic, Gemini, or Groq.

---

## 📐 Project Structure

```
querymind/
├── .env.example                  ← copy to .env and configure
├── .gitignore
├── .gitattributes
├── docker-compose.yml            ← single-command full-stack deployment
├── Makefile                      ← shortcut commands (make up, make down, etc.)
├── README.md
├── DEPLOYMENT_AND_INTEGRATION.md
├── TECHNICAL_ARCHITECTURE.md
│
├── docs/
│   └── DATA_ARCHITECTURE.md      ← full data storage reference
│
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   └── db_init.py            ← auto-creates MySQL/PG database on startup
│   ├── models/
│   │   ├── db_models.py          ← SQLAlchemy ORM models
│   │   └── schemas.py            ← Pydantic request/response schemas
│   ├── routers/
│   │   ├── __init__.py
│   │   ├── admin.py              ← auth, LLM config, DB config, file upload
│   │   ├── chat.py               ← main chat endpoint + intent routing
│   │   ├── ingest.py             ← public (no-auth) ingest endpoint
│   │   └── sessions.py           ← chat session CRUD
│   ├── services/
│   │   ├── __init__.py
│   │   ├── database_connection.py   ← SQLAlchemy engine factory + connection test
│   │   ├── embed_service.py         ← ChromaDB vector store helpers
│   │   ├── encryption.py            ← Fernet encrypt/decrypt for secrets
│   │   ├── ingest_service.py        ← file loader → chunker → embedder pipeline
│   │   ├── intent_classifier.py     ← LLM-based SQL / RAG / chat routing
│   │   ├── llm_service.py           ← unified LLM factory (5 providers)
│   │   ├── rag_service.py           ← document RAG retrieval + answer synthesis
│   │   ├── redaction_service.py     ← DLP: scans and redacts secrets from output
│   │   ├── sql_metadata_service.py  ← schema introspection + ChromaDB indexing
│   │   └── sql_rag_service.py       ← context-aware SQL generation + retry pipeline
│   ├── tests/                    ← manual smoke tests (security, integration)
│   │   ├── README.md
│   │   ├── security_test.py
│   │   ├── integration_security_test.py
│   │   └── test_cleaner.py
│   ├── tools/                    ← standalone admin utility scripts
│   │   ├── README.md
│   │   └── reset_vector_store.py ← clears ChromaDB collections for a user
│   ├── alembic/                  ← database migration scripts
│   ├── auth.py                   ← JWT + bcrypt utilities
│   ├── config.py                 ← pydantic-settings (reads .env)
│   ├── database.py               ← engine, SessionLocal, Base, get_db
│   ├── main.py                   ← FastAPI app entry point
│   ├── manage.py                 ← CLI: init-db, migrate
│   ├── migrate_db.py             ← standalone SQLite → MySQL/PG migration tool
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/
│   │   │   ├── client.js         ← axios instance, all API calls
│   │   │   └── sessionStore.js   ← session state management
│   │   ├── components/
│   │   │   └── Sidebar.jsx       ← navigation sidebar
│   │   └── pages/
│   │       ├── ChatInterface.jsx ← main chat page with SQL result tables
│   │       ├── Dashboard.jsx     ← stats overview
│   │       ├── DatabaseConfig.jsx← DB connection form
│   │       ├── KnowledgeBase.jsx ← file upload + management
│   │       ├── LLMSettings.jsx   ← provider switcher + API key form
│   │       └── LoginPage.jsx     ← authentication page
│   ├── public/
│   ├── index.html
│   ├── nginx.conf                ← production nginx config for Docker
│   ├── package.json
│   ├── Dockerfile
│   └── vite.config.js
│
├── mcp_servers/
│   ├── mcp_sql_agent.py          ← MCP tool: run SQL queries via external agents
│   └── mcp_vector_db.py          ← MCP tool: vector search via external agents
│
└── widget/
    └── chat_widget.html          ← embeddable JS chat widget (no-framework)
```

---

## 🧱 Technology Stack

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI, SQLAlchemy, LangChain ≥ 0.3 |
| **Admin UI** | React 18 + Vite 5 |
| **Vector Store** | ChromaDB (local persistent) |
| **LLM Providers** | Ollama · OpenAI · Anthropic · Gemini · Groq |
| **Embeddings** | Ollama `nomic-embed-text` |
| **App Database** | SQLite (dev) · MySQL · PostgreSQL |
| **Auth** | JWT Bearer + bcrypt hashing |
| **Encryption** | Fernet symmetric encryption (cryptography) |
| **MCP Support** | Model Context Protocol servers |
| **Deployment** | Docker Compose (7-service stack) |

---

## 🔐 Security Architecture

QueryMind implements a **defense-in-depth** security model:

| Layer | Mechanism |
|---|---|
| **Pre-LLM SQL Guard** | DML keywords (`DROP`, `DELETE`, `UPDATE`, ...) blocked via regex *before* the LLM is invoked |
| **Secret Encryption at Rest** | DB URLs and API keys encrypted with Fernet before being written to the database |
| **Internal Table Protection** | `admin_users`, `admin_settings`, etc. are explicitly forbidden in SQL WHERE/FROM clauses |
| **Output DLP Redaction** | All LLM responses are scanned for API keys, passwords, and DB URLs before being returned |
| **Tenant Isolation** | All ChromaDB collections and metadata prefixed with `user_{id}` |
| **JWT Sessions** | Stateless short-lived tokens; configurable expiry in `.env` |
| **Backward-Compatible Decryption** | Plain-text fallback safely handles pre-encryption legacy data |

---

## ⚡ Quick Start — Option A: Docker (Recommended)

This spins up the entire stack (backend, React/Nginx frontend, MySQL, Redis, ChromaDB, Ollama) with a single command.

### Prerequisites
- **Docker Desktop** — [docker.com](https://www.docker.com/products/docker-desktop/)

### Steps

```bash
# 1. Clone the repository
git clone <repo-url>
cd querymind

# 2. Configure environment
cp .env.example .env
# Edit .env — set JWT_SECRET_KEY, FERNET_KEY, ADMIN_USERNAME, ADMIN_PASSWORD

# 3. Start all services
docker-compose up --build

# Or in the background:
docker-compose up -d --build
```

Access:
- **Admin UI**: http://localhost:5173
- **API Docs (Swagger)**: http://localhost:8000/docs

Stop everything:
```bash
docker-compose down
```

---

## ⚡ Quick Start — Option B: Local Development

Use this if you want hot-reload during development.

### Prerequisites
- **Python 3.10+** — [python.org](https://www.python.org/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Ollama** (optional) — [ollama.com](https://ollama.com/)

### Step 1 — Clone & Configure

```bash
git clone <repo-url>
cd querymind
cp .env.example .env
# Edit .env with your settings
```

### Step 2 — Backend Setup

```bash
# Create and activate virtual environment
python -m venv venv

# Windows PowerShell
.\venv\Scripts\Activate.ps1

# macOS / Linux
source venv/bin/activate

# Install dependencies
cd backend
pip install -r requirements.txt
```

### Step 3 — Start Backend

```bash
cd backend
uvicorn main:app --reload --port 8000
```

✅ Backend: http://localhost:8000  
📖 Swagger: http://localhost:8000/docs

### Step 4 — Start Frontend

In a **new terminal**:

```bash
cd frontend
npm install
npm run dev
```

✅ Admin UI: http://localhost:5173

### Step 5 — Log In

Navigate to http://localhost:5173 and use the credentials from your `.env` file (`ADMIN_USERNAME` / `ADMIN_PASSWORD`).

---

## 🔑 Required Environment Variables

Open `.env` (copied from `.env.example`) and configure at minimum:

```env
# REQUIRED — generate with: python -c "import secrets; print(secrets.token_hex(32))"
JWT_SECRET_KEY=your_random_long_secret_here

# REQUIRED — generate with: python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
FERNET_KEY=your_fernet_key_here

# Admin credentials
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123

# LLM Provider
LLM_PROVIDER=ollama   # ollama | openai | anthropic | gemini | groq

# Fill in the key for your chosen provider
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
```

---

## 🖥️ Admin Panel Features

| Page | Features |
|---|---|
| **Dashboard** | Indexed tables count, knowledge files, DB connection status, LLM provider |
| **Chat** | Multi-session GPT-style chat, SQL result tables, source badges (SQL/RAG/System) |
| **Databases** | Connect MySQL / PostgreSQL / SQLite via form or direct URL |
| **Knowledge Base** | Upload PDFs, DOCX, TXT, CSV, JSON, SQL · View and delete indexed files |
| **LLM Settings** | Switch providers, enter API key, set custom Ollama URL and model |

---

## 🔌 MCP Integration (Model Context Protocol)

QueryMind tools can be used by any MCP-compatible external agent (e.g., Claude Desktop):

```bash
# SQL data tool
python mcp_servers/mcp_sql_agent.py

# Vector document search tool
python mcp_servers/mcp_vector_db.py
```

---

## 📡 API Endpoints

| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/admin/register` | No | Create a new admin account |
| `POST` | `/admin/token` | No | Login — returns JWT token |
| `GET` | `/admin/stats` | ✅ | Dashboard stats |
| `POST` | `/admin/llm-config` | ✅ | Set LLM provider + API key |
| `GET` | `/admin/llm-config` | ✅ | Get current LLM config |
| `POST` | `/admin/db-config` | ✅ | Connect and index a database |
| `GET` | `/admin/db-config` | ✅ | Get current DB config |
| `DELETE` | `/admin/db-config` | ✅ | Disconnect database |
| `POST` | `/admin/upload` | ✅ | Upload and embed a file |
| `GET` | `/admin/files` | ✅ | List indexed knowledge files |
| `DELETE` | `/admin/files/{name}` | ✅ | Delete a file from knowledge base |
| `POST` | `/chat` | No | Send a chat message |
| `GET` | `/sessions` | No | List all chat sessions |
| `POST` | `/sessions` | No | Create a new chat session |
| `DELETE` | `/sessions/{id}` | No | Delete a session |
| `PATCH` | `/sessions/{id}` | No | Rename a session |
| `GET` | `/chat/health` | No | Health check |

---

## 🛠️ Admin Tools (CLI)

```bash
# Initialize the database (creates tables)
python manage.py init-db

# Migrate from SQLite to MySQL/PostgreSQL
python manage.py migrate "sqlite:///./querymind_metadata.db" "mysql+pymysql://user:pass@host:3306/dbname"

# Reset a user's ChromaDB vector store (run from backend/)
python tools/reset_vector_store.py
```

---

## 🤝 Contributing

Open an issue or submit a pull request. Please follow PEP8 for backend code and maintain service-level separation. Document any API contract changes in `schemas.py`.
