# How to Upload QueryMind to GitHub

Follow these steps to push the full QueryMind project (backend + React frontend) to GitHub.

---

## Prerequisites

- A [GitHub account](https://github.com/)
- [Git installed](https://git-scm.com/) on your machine
- Python 3.11+ and Node.js 20+ installed

---

## Step 1 — Verify .gitignore is Correct

The `.gitignore` already excludes sensitive and auto-generated files:

```text
venv/
.venv/
node_modules/         ← frontend dependencies (large, auto-installed)
.env                  ← contains API keys and secrets — NEVER commit this
__pycache__/
*.db                  ← local SQLite files
chroma_db/            ← local vector storage
uploads/              ← local file uploads
frontend/dist/        ← production build output (built in Docker)
```

> **IMPORTANT**: Never commit your `.env` file. It contains API keys and JWT secrets.

---

## Step 2 — Initialize Git

```powershell
# From the querymind/ root folder
git init
```

---

## Step 3 — Stage and Commit

```powershell
git add .
git commit -m "Initial commit: QueryMind optimized single-container architecture"
```

---

## Step 4 — Link to GitHub and Push

1. Create a repository on [GitHub](https://github.com/new).
2. Run the following:

```powershell
# Replace with your actual GitHub username and repo name
git remote add origin https://github.com/yourusername/querymind.git
git branch -M main
git push -u origin main
```

---

## What Gets Pushed vs. What Stays Local

| Path | Pushed? | Why |
|---|---|---|
| `backend/` | ✅ Yes | Core API source code |
| `frontend/src/` | ✅ Yes | React source code |
| `frontend/package.json` | ✅ Yes | Dependency manifest |
| `Dockerfile` | ✅ Yes | Optimized 3-stage build |
| `.env.example` | ✅ Yes | Template for environment variables |
| `.env` | ❌ No | Contains secrets |
| `chroma_db/` | ❌ No | Persistent vector data |
| `data/` | ❌ No | Persistent SQLite data |

---

## When Someone Clones the Repository

They have two ways to run the project:

### Option A: Docker (Recommended for Production)
```bash
git clone https://github.com/yourusername/querymind.git
cd querymind
cp .env.example .env
# Edit .env and then run:
docker-compose up -d --build
```
- **Access**: http://localhost:8000 (UI + API)

### Option B: Local Development
```bash
# 1. Setup Backend
cd backend
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
uvicorn main:app --reload --port 8000

# 2. Setup Frontend (New Terminal)
cd frontend
npm install
npm run dev
```
- **UI**: http://localhost:5173
- **API**: http://localhost:8000

---

## Pushing Future Updates

```powershell
git add .
git commit -m "Brief description of changes"
git push
```
