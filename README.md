# 🧠 QueryMind — Enterprise SQL & Document Chatbot

QueryMind is a high-performance, RAG-enabled chatbot designed to bridge the gap between natural language and enterprise data. It allows users to query SQL databases (MySQL, PostgreSQL, SQLite) and internal documents using LLMs (Ollama, OpenAI, or Anthropic).

## 🚀 Quick Start (Docker)

The easiest way to run the entire stack is using Docker Compose:

1. **Clone the repository**:
   ```bash
   git clone <repo-url>
   cd querymind
   ```

2. **Configure Environment**:
   Copy `.env.example` to `.env` and update the values:
   ```bash
   cp .env.example .env
   ```
   *Note: Ensure `ADMIN_USERNAME` and `ADMIN_PASSWORD` are set for the first login.*

3. **Start the services**:
   ```bash
   docker-compose up --build
   ```

4. **Access the applications**:
   - **Admin Panel**: [http://localhost:8501](http://localhost:8501)
   - **Backend API**: [http://localhost:8000/docs](http://localhost:8000/docs)
   - **ChromaDB Web**: [http://localhost:8001](http://localhost:8001)

---

## 🛠️ Local Development Setup

If you prefer to run services manually without Docker:

### 1. Backend (FastAPI)

```bash
cd backend
python -m venv venv
source venv/Scripts/activate     # on Windows  on Linux/Mac source venv/bin/activate
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

### 2. Admin UI (Streamlit)
```bash
cd querymind
source venv/Scripts/activate
cd admin_ui
pip install streamlit requests
streamlit run app.py --server.port 8501
```

### 3. Prerequisites
- **PostgreSQL**: Required for storing admin settings and user data.
- **Redis**: Required for the task queue.
- **ChromaDB**: For vector storage (can be run locally or via Docker).
- **Ollama** (Optional): For local LLM processing. [Download here](https://ollama.com/).

---

## 🏗️ Architecture

- **Backend**: FastAPI with SQLAlchemy and LangChain.
- **Frontend**: Streamlit for Admin Panel; Embedded Widget for end-users.
- **Knowledge Base**: ChromaDB for RAG (Retrieval-Augmented Generation).
- **LLM Support**: 
  - **Local**: Ollama (phi3, llama3, etc.)
  - **Cloud**: OpenAI (GPT-4o), Anthropic (Claude 3.5 Sonnet)

---

## 📑 Key Features

- **Metadata-Driven SQL RAG**: Automatically fetches database schemas, indexes them in ChromaDB, and uses them to guide the LLM in generating accurate queries.
- **Flexible SQL Connections**: Supports connecting via individual fields or direct Connection URLs with auto-dialect detection.
- **Document Ingestion**: Upload PDFs, DOCX, and TXT files to provide additional context.
- **Multi-Tenant Isolation**: Uses tenant-based indexing in ChromaDB to keep data separate for different databases or users.
- **Safety**: Built-in SQL guardrails to restrict queries to read-only (SELECT) operations.

## 🤝 Contributing
Feel free to open issues or submit pull requests for any improvements.

