# QueryMind — Admin Tools

This directory contains standalone administrative utility scripts. These are **not** part of the main application — run them manually from the `backend/` directory when needed.

## Tools

### `reset_vector_store.py`
Clears the ChromaDB vector collections for a specific user. Use this when:
- You want to force a fresh re-upload of all documents.
- A user's knowledge base is corrupted or stale.

**Usage:**
```bash
# From backend/ directory
python tools/reset_vector_store.py
```
This resets `user_1` by default. Edit the `target_user` variable inside the script to target a different user.

> ⚠️ **Warning:** This is destructive — it permanently deletes the user's vector embeddings. The source files are NOT deleted.
