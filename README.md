# 🧠 QueryMind — AI-Powered RAG Chatbot

QueryMind is a high-performance, RAG-enabled chatbot application that provides a unified interface for querying structured data (SQL) and unstructured knowledge (PDFs, DOCX, CSV). It is designed for secure, localized deployment with support for multiple LLM providers.

---

## 🚀 Project Overview

QueryMind acts as an intelligent middleware layer that:
1. **Understands Intent**: Routes user queries to either a SQL engine (for structured data) or a Document RAG engine (for unstructured knowledge).
2. **Context-Aware Retrieval**: Fetches relevant snippets from your knowledge base or database schema to ground LLM responses.
3. **Secure & Optimized**: Features multi-stage Docker builds for minimal footprint and single-port serving of both UI and API.

---

## ✨ Key Features

- **Hybrid RAG Engine**: Query both SQL databases and uploaded documents in one chat.
- **Multi-LLM Support**: Plug-and-play with Ollama (Local), OpenAI, Anthropic, Gemini, and Groq.
- **Automated Schema Indexing**: Automatically crawls and describes your SQL database tables for natural language querying.
- **Admin Dashboard**: Comprehensive UI for managing LLM settings, database connections, and knowledge files.
- **Security-First**: Built-in SQL injection guardrails, secret encryption (Fernet), and output PII/Secret redaction.
- **High Performance**: Serving both React Frontend and FastAPI Backend from a single optimized Docker container.

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Frontend** | React 18, Vite, Axios |
| **Backend** | FastAPI (Python 3.11), SQLAlchemy, LangChain |
| **Database (Metadata)** | SQLite (Persistent via volumes) |
| **Vector Store** | ChromaDB (Local persistent) |
| **LLM Inference** | Ollama, OpenAI, Anthropic, Gemini, Groq |
| **Infrastructure** | Docker (Multi-stage), Docker Compose |

---

## 📁 Folder Structure

```text
querymind/
├── backend/                # FastAPI application source
│   ├── core/               # App initialization and settings
│   ├── models/             # SQLAlchemy DB models
│   ├── routers/            # API endpoint definitions (Auth, Chat, Admin, Ingest)
│   ├── services/           # Core logic (RAG, LLM Factory, Encryption, Ingest)
│   ├── static/             # Built React frontend assets (Production only)
│   └── main.py             # Entry point
├── frontend/               # React (Vite) application source
├── chroma_db/              # Vector database storage (git-ignored)
├── data/                   # SQLite database storage (git-ignored)
├── uploads/                # Document upload storage (git-ignored)
├── Dockerfile              # Optimized 3-stage build
└── docker-compose.yml      # Deployment configuration
```

---

## ⚙️ Local Setup (Development)

### Prerequisites
- **Python 3.11+**
- **Node.js 20+**
- **Ollama** (Optional, for local LLMs)

### 1. Backend Setup
```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp ../.env.example .env
# Start the API
uvicorn main:app --reload --port 8000
```

### 2. Frontend Setup
```bash
cd frontend
npm install
npm run dev
```
- **Admin UI**: http://localhost:5173
- **API Docs**: http://localhost:8000/docs

---

## 🐳 Docker Deployment (Azure VM / Production)

QueryMind is optimized for single-container deployment on VMs (e.g., Azure B2s/B4ms).

### 1. Prepare Environment
Copy `.env.example` to `.env` and fill in your keys:
```env
JWT_SECRET_KEY=...
FERNET_KEY=...
ADMIN_USERNAME=admin
ADMIN_PASSWORD=admin123
```

### 2. Launch with Docker Compose
```bash
docker-compose up -d --build
```

### 3. Access
- **Application**: http://<your-vm-ip>:8000
- **FastAPI Documentation**: http://<your-vm-ip>:8000/docs

---

## 🔑 Environment Variables

| Variable | Description | Default |
|---|---|---|
| `LLM_PROVIDER` | Active LLM (ollama/openai/anthropic/etc.) | `ollama` |
| `DATABASE_URL` | SQLAlchemy connection string | `sqlite:///./querymind_metadata.db` |
| `JWT_SECRET_KEY` | Key for signing Auth tokens | (Required) |
| `FERNET_KEY` | Key for encrypting DB secrets | (Required) |
| `ADMIN_USERNAME` | Initial admin username | `admin` |
| `ADMIN_PASSWORD` | Initial admin password | `admin123` |

---

## 📡 Key API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| `POST` | `/admin/token` | Login and receive JWT |
| `POST` | `/chat` | Send query and get AI response |
| `POST` | `/admin/upload` | Upload and index documents |
| `POST` | `/admin/db-config` | Configure and index SQL database |
| `GET` | `/sessions` | List active chat sessions |

---

## 🖼️ Screenshots
*(Placeholders for documentation)*
- **[Screenshot: Chat Interface]** - Natural language query over documents.
- **[Screenshot: Admin Dashboard]** - LLM and Database configuration.
- **[Screenshot: Knowledge Base]** - File management and ingestion status.

---

## 📈 Future Improvements

- **Reranking Layer**: Integrate Flashrank for higher precision retrieval.
- **Streaming Responses**: Enable real-time token streaming in UI.
- **Multi-Tenant Roles**: Granular RBAC for different admin levels.
- **Advanced SQL Support**: Support for complex JOINs and CTEs in larger schemas.

---

## 🤝 Contributing

Contributions are welcome! Please ensure all backend changes include relevant Pydantic schema updates and maintain service-level isolation.
