# QueryMind — Deployment & Integration Guide

This guide covers production deployment using Docker, environment configuration, and embedding the QueryMind chatbot into external applications.

---

## 🏗️ Stack Overview

| Component | Technology | Role |
|---|---|---|
| **Full Stack App** | FastAPI + React | Unified container serving both API and Frontend |
| **Metadata DB** | SQLite | Persistent metadata storage via Docker volumes |
| **Vector Store** | ChromaDB | High-performance semantic search indexing |
| **Deployment** | Docker Compose | Optimized single-container deployment |

---

## 🔑 Environment Configuration

QueryMind uses a `.env` file for all critical settings. Copy the template and fill in your keys:

```bash
cp .env.example .env
```

### Required Variables
| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `ollama`, `openai`, `anthropic`, `gemini`, or `groq` |
| `JWT_SECRET_KEY` | Secret for signing auth tokens (use a long random hex string) |
| `FERNET_KEY` | Key for encrypting DB credentials (base64 32-byte key) |
| `ADMIN_USERNAME` | Your admin login username |
| `ADMIN_PASSWORD` | Your admin login password |

---

## 🚀 Production Deployment (Single Container)

The recommended deployment method is using **Docker Compose** on a Linux VM (e.g., Azure B2s/B4ms).

### 1. Launch the Application
The `Dockerfile` uses a 3-stage build to minimize size and optimize performance.
```bash
# Start the container in detached mode
docker-compose up -d --build
```

### 2. Access Points
In production, both the UI and the API are served on a **single port**:
- **Web UI**: `http://<vm-ip>:8000`
- **API Docs**: `http://<vm-ip>:8000/docs`

### 3. Persistence
QueryMind uses **Named Volumes** to ensure data persists across container restarts:
- `querymind_data`: Stores the SQLite database.
- `querymind_chroma`: Stores the vector embeddings.
- `querymind_uploads`: Stores the raw uploaded documents.

---

## 🤖 Integrating the Chatbot Widget

You can embed the QueryMind chatbot into any external website using the provided widget.

### 1. The Widget File
Located at: `querymind/widget/chat_widget.html`

### 2. Configuration
Update the `API_URL` in the widget script to point to your deployed backend:
```javascript
const API_URL = "http://<your-vm-ip>:8000";
```

### 3. Embedding
Copy the contents of `chat_widget.html` into your application's HTML or reference it as an iframe/script depending on your host environment.

---

## 🛠️ Security Architecture

QueryMind implements a **defense-in-depth** model:
- **JWT Auth**: All administrative routes are protected by stateless JWT tokens.
- **SQL Guardrails**: Prevents DML (DROP, DELETE, etc.) execution via natural language.
- **Encryption**: Database connection strings and API keys are encrypted at rest using Fernet.
- **DLP Redactor**: Automatically masks secrets and API keys in LLM responses.

---

## 📋 Common Maintenance Commands

### Viewing Logs
```bash
docker logs -f querymind
```

### Restarting Services
```bash
docker-compose restart
```

### Cleaning Up
```bash
docker-compose down
```
*(Note: Named volumes are preserved unless the `-v` flag is used)*
