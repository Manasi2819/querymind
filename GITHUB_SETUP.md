# How to Upload QueryMind to GitHub

Follow these steps to upload your project to a new GitHub repository properly.

## Prerequisites
- A [GitHub account](https://github.com/).
- [Git installed](https://git-scm.com/) on your local machine.
- Your project files are organized and ready.

## Step 1: Initialize Git
If you haven't already initialized your project, open your terminal (PowerShell or Git Bash) from the project directory (`c:\Users\Admin\Documents\chatbot1\querymind`) and run:

```bash
# Initialize a new Git repository
git init
```

## Step 2: Configure .gitignore
We have already created a `.gitignore` file for you, which includes:
- Virtual environments (`venv/`, `.venv/`)
- Environment variables (`.env`)
- Python cache (`__pycache__/`)
- Database files (`*.db`, `chroma_db/`)
- Temporary uploads (`uploads/`)

**IMPORTANT**: Never push your `.env` file to GitHub as it contains sensitive API keys and database credentials.

## Step 3: Add Files to Staging
Add all your project files to the Git staging area:

```bash
# Add all files (excluding those in .gitignore)
git add .
```

To verify which files are being added, you can run:
```bash
# Check the status of your staged files
git status
```

## Step 4: Create Initial Commit
Commit your files with a descriptive message:

```bash
# Commit the staged files
git commit -m "Initial commit: QueryMind Chatbot Platform"
```

## Step 5: Create a Repository on GitHub
1. Go to [github.com/new](https://github.com/new).
2. Enter a name for your repository (e.g., `querymind-chatbot`).
3. Choose **Public** or **Private**.
4. **Do NOT** initialize with a README, .gitignore, or License (since we already have them).
5. Click **Create repository**.

## Step 6: Link Local Repo to GitHub
Copy the remote repository URL from GitHub (e.g., `https://github.com/yourusername/querymind-chatbot.git`) and run:

```bash
# Add the remote repository address
git remote add origin https://github.com/yourusername/querymind-chatbot.git

# Set the main branch (standard)
git branch -M main
```

## Step 7: Push to GitHub
Finally, push your code to the remote repository:

```bash
# Push the local 'main' branch to 'origin'
git push -u origin main
```

---

### Troubleshooting
- **Permission Denied**: Ensure you are logged into Git on your machine. You may need to run `git config --global user.name "Your Name"` and `git config --global user.email "your@email.com"`.
- **Large Files**: If you have very large files, consider using [Git LFS](https://git-lfs.github.com/).
- **Updating Code**: To push new changes in the future, just run:
  1. `git add .`
  2. `git commit -m "Your update message"`
  3. `git push`
