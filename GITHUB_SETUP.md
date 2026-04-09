# How to Upload QueryMind to GitHub

Follow these steps to push the full QueryMind project (backend + React frontend) to GitHub.

---

## Prerequisites

- A [GitHub account](https://github.com/)
- [Git installed](https://git-scm.com/) on your machine
- Node.js 18+ installed (for the React frontend)

---

## Step 1 — Verify .gitignore is Correct

The `.gitignore` already excludes sensitive and auto-generated files:

```
venv/
.venv/
node_modules/         ← frontend dependencies (large, auto-installed)
.env                  ← contains API keys and secrets — NEVER commit this
__pycache__/
*.db
chroma_db/
uploads/
frontend/dist/        ← production build output
```

> **IMPORTANT**: Never commit your `.env` file. It contains API keys and JWT secrets.

---

## Step 2 — Initialize Git (if not already done)

```powershell
# From the querymind/ root folder
git init
```

---

## Step 3 — Configure Your Git Identity (first time only)

```powershell
git config --global user.name "Your Name"
git config --global user.email "your@email.com"
```

---

## Step 4 — Stage All Files

```powershell
# Add all tracked files (gitignore will exclude venv, node_modules, .env, etc.)
git add .

# Verify what is staged — check that .env and venv/ are NOT listed
git status
```

---

## Step 5 — Create Initial Commit

```powershell
git commit -m "Initial commit: QueryMind with React frontend"
```

---

## Step 6 — Create a Repository on GitHub

1. Go to [github.com/new](https://github.com/new)
2. Enter a repository name, e.g. `querymind-chatbot`
3. Choose **Public** or **Private**
4. **Do NOT** check "Initialize with README", `.gitignore`, or License
5. Click **Create repository**

---

## Step 7 — Link to GitHub and Push

```powershell
# Replace with your actual GitHub username and repo name
git remote add origin https://github.com/yourusername/querymind-chatbot.git

# Set main as default branch
git branch -M main

# Push to GitHub
git push -u origin main
```

---

## Step 8 — Add README Badge (optional)

After pushing, your README.md will automatically render on GitHub. You can add status badges at the top:

```markdown
![Python](https://img.shields.io/badge/python-3.10+-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green)
![React](https://img.shields.io/badge/React-18-61DAFB)
![Vite](https://img.shields.io/badge/Vite-5-purple)
```

---

## What Gets Pushed vs. What Stays Local

| Path | Pushed? | Why |
|---|---|---|
| `backend/` | ✅ Yes | Core API code |
| `frontend/src/` | ✅ Yes | React source code |
| `frontend/package.json` | ✅ Yes | Dependency manifest |
| `frontend/node_modules/` | ❌ No | Auto-installed via `npm install` |
| `frontend/dist/` | ❌ No | Build output, regenerated |
| `widget/` | ✅ Yes | Embeddable chat widget |
| `.env` | ❌ No | Contains secrets |
| `.env.example` | ✅ Yes | Template for others |
| `venv/` | ❌ No | Python env, large |
| `chroma_db/` | ❌ No | Local vector DB data |
| `*.db` files | ❌ No | Local database files |

---

## When Someone Clones the Repository

They follow these steps to get started:

```powershell
# 1. Clone
git clone https://github.com/yourusername/querymind-chatbot.git
cd querymind-chatbot

# 2. Copy and configure environment
copy .env.example .env
# (Edit .env with your keys)

# 3. Set up Python environment
python -m venv venv
.\venv\Scripts\Activate.ps1      # Windows
# OR: source venv/bin/activate   # Mac/Linux
cd backend
pip install -r requirements.txt
cd ..

# 4. Start the backend
cd backend
uvicorn main:app --reload --port 8000

# 5. (New terminal) register admin user — first time only
Invoke-RestMethod -Uri "http://localhost:8000/admin/register" `
  -Method POST -ContentType "application/json" `
  -Body '{"username": "admin", "password": "admin123"}'

# 6. (New terminal) Start the React frontend
cd frontend
npm install
npm run dev

# 7. Open in browser
# http://localhost:5173  → React Admin Panel
# http://localhost:8000/docs → API Docs
```

---

## Pushing Future Updates

```powershell
git add .
git commit -m "Description of your changes"
git push
```

---

## Troubleshooting

| Issue | Fix |
|---|---|
| `Permission denied (publickey)` | Use HTTPS URL instead of SSH, or add SSH key to GitHub |
| `node_modules` is being staged | Make sure `frontend/node_modules/` is in `.gitignore` |
| `.env` showing in `git status` | Add `.env` to `.gitignore` and run `git rm --cached .env` |
| `git push` rejected | Run `git pull --rebase origin main` first |
