# QueryMind — Deployment & Integration Guide

This guide covers production deployment, multi-user setup, and embedding the chatbot widget into external web applications.

---

## 🏗️ Stack Overview

| Component | Technology | Port |
|---|---|---|
| Backend API | FastAPI + Uvicorn | 8000 |
| React Admin Panel | Vite + React 18 | 5173 |
| Vector Store | ChromaDB (local) | — |
| Metadata DB | SQLite | — |

---

## 🚀 Production Deployment

### Option A — Manual (Recommended for Development)

#### Terminal 1 — Backend

```powershell
# From querymind/ root
.\venv\Scripts\Activate.ps1          # Windows PowerShell
# OR: source venv/bin/activate       # Mac / Linux

cd backend
uvicorn main:app --host 0.0.0.0 --port 8000
```

> Remove `--reload` flag in production (it's for dev only).

#### Terminal 2 — React Frontend (Dev Server)

```powershell
cd frontend
npm run dev
```

> For production builds (served by a static host or nginx):
> ```powershell
> cd frontend
> npm run build       # outputs to frontend/dist/
> ```

---

### Option B — Docker Compose

```powershell
# From querymind/ root:

# Build and start all backend services
docker-compose up -d --build

# Then start the React frontend (Vite dev server):
cd frontend
npm install
npm run dev
```

Access:
- React Admin Panel → http://localhost:5173
- Backend API Docs → http://localhost:8000/docs

> **Note:** The `docker-compose.yml` covers the FastAPI backend and ChromaDB. The React frontend runs via `npm run dev` or a static server.

---

## 👤 First-Time Admin Setup

After the backend is running, register the admin user **once**:

```powershell
# Windows PowerShell
Invoke-RestMethod -Uri "http://localhost:8000/admin/register" `
  -Method POST `
  -ContentType "application/json" `
  -Body '{"username": "admin", "password": "admin123"}'
```

```bash
# curl (Linux / Mac / Git Bash)
curl -X POST http://localhost:8000/admin/register \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

Expected response:
```json
{ "message": "User registered successfully", "user_id": 1 }
```

---

## 👥 Multi-User Setup

QueryMind supports multiple independent users with fully isolated data.

### Register Additional Users

```bash
curl -X POST http://localhost:8000/admin/register \
  -H "Content-Type: application/json" \
  -d '{"username": "vendor_a", "password": "secure_pass_1"}'

curl -X POST http://localhost:8000/admin/register \
  -H "Content-Type: application/json" \
  -d '{"username": "vendor_b", "password": "secure_pass_2"}'
```

### How Isolation Works

Each user gets their own:
- JWT token (obtained via `POST /admin/token`)
- Database connection config
- ChromaDB collection (prefixed with `user_{id}_document` and `user_{id}_knowledge_base`)
- Uploaded file records

**Vendor A cannot access Vendor B's data — ever.**

---

## 🔑 Getting a JWT Token (for API Testing)

```bash
curl -X POST http://localhost:8000/admin/token \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin&password=admin123"
```

Response:
```json
{ "access_token": "eyJ...", "token_type": "bearer" }
```

Use the token in subsequent requests:
```bash
curl -H "Authorization: Bearer eyJ..." http://localhost:8000/admin/stats
```

---

## 🤖 Chatbot Widget — Embedding in External Apps

The embeddable widget lets any web application host a QueryMind chatbot for a specific user.

### Widget File Location
```
querymind/widget/chat_widget.html
```

### Configuration

In the widget's script block, set:

```javascript
const API_URL = "https://your-deployed-api.com";  // Your backend URL
const USER_ID = 2;                                  // The user's ID
```

### Embedding

Copy the HTML/CSS/JS from `chat_widget.html` into your app's HTML footer. The widget will:
1. Show a chat icon in the bottom-right corner
2. Target the specific knowledge base of the configured `USER_ID`
3. Answer questions using only that user's data (their DB + uploaded files)

### Testing Multi-Tenant Isolation

To verify that two users see only their own data:
1. Embed the widget with `USER_ID = 1` on Page A
2. Embed the widget with `USER_ID = 2` on Page B
3. Ask the same data question on both pages — answers should differ based on each user's configured data

---

## 🔧 Environment Variables Reference

| Variable | Required | Description |
|---|---|---|
| `LLM_PROVIDER` | ✅ | `ollama`, `openai`, `anthropic`, `gemini`, or `groq` |
| `JWT_SECRET_KEY` | ✅ | Long random string for signing JWT tokens |
| `FERNET_KEY` | ✅ | Base64-encoded securely generated key for database URL encryption |
| `JWT_EXPIRE_MINUTES` | — | Token lifetime in minutes (default: 1440 = 24h) |
| `OPENAI_API_KEY` | If using OpenAI | Your OpenAI API key |
| `ANTHROPIC_API_KEY` | If using Anthropic | Your Anthropic API key |
| `GEMINI_API_KEY` | If using Gemini | Your Gemini API key |
| `GROQ_API_KEY` | If using Groq | Your Groq API key |
| `OLLAMA_BASE_URL` | If using Ollama | Default: `http://localhost:11434` |
| `CHROMA_PERSIST_DIR` | — | Where ChromaDB stores data (default: `./chroma_db`) |
| `UPLOAD_DIR` | — | Where uploaded files are saved (default: `./uploads`) |
| `ADMIN_USERNAME` | — | Shown in `.env.example` only — register via API |
| `ADMIN_PASSWORD` | — | Shown in `.env.example` only — register via API |

---

## 📋 Complete API Reference

### Authentication
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/admin/register` | None | Register a new user |
| `POST` | `/admin/token` | None | Login → get JWT |

### Dashboard
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/stats` | JWT | Get system stats (files, tables, LLM) |

### LLM Configuration
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/llm-config` | JWT | View current LLM provider |
| `POST` | `/admin/llm-config` | JWT | Switch provider (ollama / openai / anthropic / gemini / groq) |

### Database Configuration
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/db-config` | JWT | View current DB connection |
| `POST` | `/admin/db-config` | JWT | Connect a database |
| `DELETE` | `/admin/db-config` | JWT | Disconnect the database |

### Knowledge Base
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `GET` | `/admin/files` | JWT | List all uploaded/indexed files |
| `POST` | `/admin/upload` | JWT | Upload and index a file |
| `DELETE` | `/admin/files/{filename}` | JWT | Delete a file from knowledge store |

### Chat & Sessions
| Method | Endpoint | Auth | Description |
|---|---|---|---|
| `POST` | `/chat` | None* | Send a message, get an AI answer |
| `GET` | `/sessions` | JWT | Get all chat sessions for user |
| `POST` | `/sessions` | JWT | Create a new session |
| `GET` | `/sessions/{id}` | JWT | Get chat history for specific session |
| `DELETE` | `/sessions/{id}` | JWT | Delete a session |
| `PATCH` | `/sessions/{id}` | JWT | Update the title of a session |

> *The `/chat` and `/sessions` endpoints use `user_id` internally. The React Admin panel dynamically fetches these.
