# QueryMind — Deployment & Integration Guide

This guide covers production deployment, environment configuration, and how to embed the QueryMind chatbot into any external web application.

---

## 🏗️ Stack Overview

| Component | Technology | Role |
|---|---|---|
| **Backend API** | FastAPI + Uvicorn | Request handling, LLM orchestration, and RAG logic |
| **Admin Panel** | Vite + React | Dashboard for managing DB connections and Knowledge Base |
| **Metadata DB** | SQLite (default) | Stores users, settings, and file records |
| **Vector Store** | ChromaDB | High-performance semantic search for context retrieval |

---

## 🔑 Environment Configuration

QueryMind uses a `.env` file for all critical settings. Before deploying, copy the example file and fill in your keys:

```bash
cp .env.example .env
```

### Required Variables
| Variable | Description | Example |
|---|---|---|
| `LLM_PROVIDER` | AI provider to use | `ollama`, `openai`, `gemini`, etc. |
| `JWT_SECRET_KEY` | Random string for signing tokens | `openssl rand -hex 32` |
| `FERNET_KEY` | Key for encrypting DB credentials | Generate via `cryptography.fernet` |
| `ADMIN_USERNAME` | Default admin login (seeded on starts) | `admin` |
| `ADMIN_PASSWORD` | Default admin password | `password123` |

### Provider Specific (Fill at least one)
- `OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `GEMINI_API_KEY`, `GROQ_API_KEY`
- `OLLAMA_BASE_URL` (Default: `http://localhost:11434`)

### Database Overrides (Optional)
| Variable | Description | Example |
|---|---|---|
| `DATABASE_URL` | SQLAlchemy connection string | `postgresql://user:pass@host/db` |
| `CHROMA_PERSIST_DIR` | Folder for vector storage | `./chroma_db` |

---

## 🚀 Production Deployment

### Option A — Docker Compose (Recommended)

Docker is the easiest way to run QueryMind in production. It orchestrates the backend, frontend, and databases automatically.

```powershell
# From the project root
docker-compose up -d --build
```

**Access Points:**
- **Admin Dashboard**: http://localhost (Port 80)
- **Backend API**: http://localhost:8000
- **Ollama Engine**: http://localhost:11434

### Option B — Using Local LLMs (Ollama)

If you chose to run AI locally using the included Ollama service, you must download the models after the containers are started:

```powershell
# Pull the chat model
docker exec -it querymind-ollama ollama pull llama3.2:3b

# Pull the embedding model (required for Knowledge Base)
docker exec -it querymind-ollama ollama pull nomic-embed-text
```

---

### Option C — Manual Deployment

1. **Backend**:
   ```powershell
   cd backend
   pip install -r requirements.txt
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

2. **Frontend**:
   ```powershell
   cd frontend
   npm install
   npm run build
   # Serve the 'dist' folder using Nginx, Apache, or a static host like Vercel.
   ```

---

## 👤 First-Time Setup

1. **Automatic Seeding**: On the first run, the system automatically creates the admin user from your `.env` variables (`ADMIN_USERNAME` and `ADMIN_PASSWORD`).
2. **Login**: Visit the Admin Panel and log in with those credentials.
3. **Connect Data**:
   - Go to **Database Config** to link your operational database (MySQL/Postgres/etc).
   - Go to **Knowledge Base** to upload PDF/Text files for semantic search.

---

## 🤖 Integrating the Chatbot Widget

The QueryMind widget is designed to be "pluggable" into any host website (e.g., a CRM, E-commerce site, or internal portal).

### 1. Locate the Widget
The standalone HTML/JS implementation is found at:
`querymind/widget/chat_widget.html`

### 2. Configure the Integration
Open the widget file and update the configuration block:

```javascript
const API_URL = "https://your-api-domain.com"; // Your deployed backend URL
const USER_ID = 1;                             // Your unique Vendor/Admin ID
```

### 3. Embed in Your App
Paste the widget markup and script into your host application's footer. 

> [!TIP]
> **Multi-App Isolation**: If you have multiple distinct applications or clients, you can create separate user IDs in the database and use their specific `user_id` in their respective widget configurations. QueryMind automatically isolates chat history and knowledge bases based on this ID.

---

## 📋 API Reference Summary

| Endpoint | Method | Auth | Usage |
|---|---|---|---|
| `/admin/token` | `POST` | None | Login to get JWT access token |
| `/chat` | `POST` | None | Main chat endpoint (Requires `user_id`) |
| `/admin/db-config` | `POST` | JWT | Connect a database to the AI |
| `/admin/upload` | `POST` | JWT | Add documents to the Knowledge Base |
| `/sessions` | `GET` | JWT | Retrieve chat history for the user |

---

## 🛠️ Scaling for Production

For high-traffic deployments:
- **Metadata**: Switch from SQLite to **Postgres** for better concurrency.
- **Files**: Ensure the `uploads/` and `chroma_db/` volumes are backed up regularly.
- **LLM**: Use a cloud provider (OpenAI/Gemini) or a high-performance local Ollama server on a dedicated GPU node.
