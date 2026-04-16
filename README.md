# 🧠 QueryMind — Enterprise SQL & Document Chatbot

QueryMind is a high-performance, RAG-enabled chatbot that bridges the gap between natural language and enterprise data. Query SQL databases (MySQL, PostgreSQL, SQLite) and internal documents using LLMs — powered by Ollama (local), OpenAI, or Anthropic.

---

## 📐 Architecture Overview

```
querymind/
├── .env.example              ← copy to .env and configure
├── .gitignore
├── docker-compose.yml
├── README.md
├── DEPLOYMENT_AND_INTEGRATION.md
├── TECHNICAL_ARCHITECTURE.md
│
├── backend/
│   ├── core/
│   │   ├── __init__.py
│   │   └── db_init.py        ← auto-creates MySQL/PG database on startup
│   ├── models/
│   │   ├── db_models.py      ← SQLAlchemy ORM models
│   │   └── schemas.py        ← Pydantic request/response schemas
│   ├── routers/
│   │   ├── admin.py          ← auth, LLM config, DB config, file upload
│   │   ├── chat.py           ← main chat endpoint + intent routing
│   │   ├── ingest.py         ← public (no-auth) ingest endpoint
│   │   └── sessions.py       ← chat session CRUD
│   ├── services/
│   │   ├── database_connection.py   ← SQLAlchemy engine factory
│   │   ├── embed_service.py         ← ChromaDB vector store helpers
│   │   ├── encryption.py            ← Fernet encrypt/decrypt for secrets
│   │   ├── ingest_service.py        ← file loader → chunker → embedder
│   │   ├── intent_classifier.py     ← LLM-based SQL / RAG / chat routing
│   │   ├── llm_service.py           ← unified LLM factory (5 providers)
│   │   ├── rag_service.py           ← document RAG retrieval + answer
│   │   ├── sql_metadata_service.py  ← schema introspection → ChromaDB
│   │   └── sql_rag_service.py       ← context-aware SQL generation pipeline
│   ├── tests/                ← pytest unit tests
│   ├── alembic/              ← database migration scripts
│   ├── auth.py               ← JWT + bcrypt utilities
│   ├── config.py             ← pydantic-settings (reads .env)
│   ├── database.py           ← engine, SessionLocal, Base, get_db
│   ├── main.py               ← FastAPI app entry point
│   ├── manage.py             ← CLI: init-db, migrate
│   ├── migrate_db.py         ← standalone SQLite → MySQL/PG migration tool
│   ├── reset_vector_store.py ← utility: clear ChromaDB collections for a user
│   ├── alembic.ini
│   ├── Dockerfile
│   └── requirements.txt
│
├── frontend/
│   ├── src/
│   │   ├── api/              ← axios client + session store
│   │   ├── components/       ← Sidebar
│   │   └── pages/            ← Chat, Dashboard, DB Config, KB, LLM, Login
│   ├── package.json
│   └── vite.config.js
│
├── mcp_servers/
│   ├── mcp_sql_agent.py      ← MCP tool: run SQL queries
│   └── mcp_vector_db.py      ← MCP tool: vector search
│
└── widget/                   ← embeddable JS chat widget
```

| Layer | Technology |
|---|---|
| **Backend API** | FastAPI, SQLAlchemy, LangChain |
| **Admin UI** | React 18 + Vite (proxies routing automatically) |
| **MCP Tooling** | Model Context Protocol (MCP) servers |
| **Vector Store** | ChromaDB (local persistence) |
| **LLM** | Ollama (local) · OpenAI · Anthropic · Gemini · Groq |
| **Auth** | JWT Bearer tokens |

> **For an in-depth visual dive into how the core loops communicate, read the new [TECHNICAL_ARCHITECTURE.md](./TECHNICAL_ARCHITECTURE.md) blueprint.**

---

## 🔌 Model Context Protocol (MCP)
QueryMind now supports **MCP**, allowing your SQL and Document search capabilities to be used by external AI agents.

### Setup MCP Tools:
1.  **Run a server**:
    ```bash
    # For SQL Data tool:
    python mcp_servers/mcp_sql_agent.py
    
    # For Vector search tool:
    python mcp_servers/mcp_vector_db.py
    ```
2.  **Claude Desktop Config**:
    Add the server path to your `claude_desktop_config.json` to empower Claude with your QueryMind data brains.

---

## ⚡ Quick Start — Local Development (Step by Step)

### Prerequisites
Ensure these are installed before starting:
- **Python 3.10+** — [python.org](https://www.python.org/)
- **Node.js 18+** — [nodejs.org](https://nodejs.org/)
- **Git** — [git-scm.com](https://git-scm.com/)
- **Ollama** (optional, for local LLM) — [ollama.com](https://ollama.com/)

---

### Step 1 — Clone the Repository

```powershell
git clone <repo-url>
cd querymind
```

---

### Step 2 — Configure Environment

```powershell
# Copy the example env file
copy .env.example .env
```

Open `.env` and update at minimum:

```env
JWT_SECRET_KEY=your_random_long_secret_here   # REQUIRED — change this
FERNET_KEY=EUnxK17YIzJNolks8lKU3Lx_XZlZ-LthG026S_avWSY= # REQUIRED — for DB URL encryption
ADMIN_USERNAME=admin                           # default admin username
ADMIN_PASSWORD=admin123                        # default admin password

# Selected LLM provider inside system:
LLM_PROVIDER=openai       # or: ollama / anthropic / gemini / groq

# LLM API Keys (fill according to choice):
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIzaSy...
GROQ_API_KEY=gsk_...
```

---

### Step 3 — Set Up Python Virtual Environment

Run these commands from the **root `querymind/` folder**:

```powershell
# Create virtual environment
python -m venv venv

# Activate it (Windows PowerShell)
.\venv\Scripts\Activate.ps1

# Activate it (Windows CMD)
venv\Scripts\activate.bat

# Activate it (Mac / Linux)
source venv/bin/activate
```

> You should see `(venv)` appear at the start of your terminal prompt.

---

### Step 4 — Install Backend Dependencies

```powershell
# Make sure (venv) is active, then:
cd backend
pip install -r requirements.txt
cd ..
```

---

### Step 5 — Start the Backend API

Open a **new terminal window**, activate the venv, then:

```powershell
.\venv\Scripts\Activate.ps1     # Windows PowerShell
# OR
source venv/bin/activate        # Windows PowerShell
# OR
source venv/bin/activate         # Mac / Linux

cd backend
uvicorn main:app --reload --port 8000
```

✅ Backend is running at: **http://localhost:8000**  
📖 API Docs (Swagger): **http://localhost:8000/docs**

> Keep this terminal open. Do not close it.

---

---

### Step 6 — Start the React Frontend

Open **another new terminal window** (no venv needed here):

```powershell
cd frontend
npm install        # only needed the first time
npm run dev
```

✅ React Admin Panel is running at: **http://localhost:5173**

> Keep this terminal open. Vite watches for file changes and hot-reloads.

---

### Step 7 — Log In

1. Open your browser at **http://localhost:5173**
2. Enter the credentials you configured in your **.env** file:
   - **Username**: (Default: `admin`)
   - **Password**: (Default: `admin123`)
3. Click **Sign In**

---

## 🖥️ Admin Panel — Pages & Features

After logging in, the left sidebar gives you access to:

| Sidebar Item | What It Does |
|---|---|
| **Dashboard** | System stats (indexed tables, knowledge files, LLM provider), DB connection status |
| **+ New Chat** | Opens a fresh chat session (GPT-style multi-session history) |
| **Recent History** | Your previous chat sessions listed in the sidebar |
| **Databases** | Configure MySQL / PostgreSQL / SQLite connection (fields or direct URL) |
| **Knowledge** | Upload PDFs, DOCX, TXT, SQL, JSON, CSV · View and delete indexed files |
| **LLM Settings** | Switch between Ollama (local) and cloud API (OpenAI / Anthropic) |
| **🌙 Dark/Light toggle** | Top-right button — persists across refreshes |

---

## 🐳 Docker Quick Start (Alternative)

If you prefer Docker instead of running services manually:

```powershell
# Start all services (backend + ChromaDB)
docker-compose up --build

# Run in background
docker-compose up -d --build
```

Then start the React frontend separately:

```powershell
cd frontend
npm install
npm run dev
```

Access:
- **React Admin Panel**: http://localhost:5173
- **Backend API Docs**: http://localhost:8000/docs

---

## 📡 API Endpoints Reference

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/token` | Login and get JWT token |
| `GET` | `/admin/stats` | Dashboard stats |
| `POST` | `/admin/llm-config` | Set LLM provider |
| `GET` | `/admin/llm-config` | Get current LLM config |
| `POST` | `/admin/db-config` | Connect a database |
| `GET` | `/admin/db-config` | Get current DB config |
| `DELETE` | `/admin/db-config` | Disconnect database |
| `POST` | `/admin/upload` | Upload and index a file |
| `GET` | `/admin/files` | List indexed files |
| `DELETE` | `/admin/files/{name}` | Delete a file |
| `POST` | `/chat` | Send a chat message |
| `GET` | `/sessions` | View and load chat history sessions |
| `POST` | `/sessions` | Construct a new chat session branch |

---

## 📑 Key Features

- **Hybrid SQL - RAG Logic** — Intelligently routes between SQL (structured) and Document (unstructured) retrieval.
- **Model Context Protocol (MCP)** — Seamlessly plug your QueryMind data into external AI systems.
- **Metadata-Driven SQL RAG** — Auto-fetches DB schemas, indexes them in ChromaDB, and guides the LLM safely.
- **Safe SQL Execution** — Built-in guardrails restrict to read-only `SELECT` statements via automated self-correction loops.
- **Multi-Tenant Isolation** — Native `tenant_id` partitioning ensures enterprise data separation.
- **GPT-Style Chat UI** — Multi-session history, dynamic SQL expander, and dark mode.

---

## 🤝 Contributing

Open an issue or submit a pull request for improvements. Please follow the existing code style and document any API changes.
