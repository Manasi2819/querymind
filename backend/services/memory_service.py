"""
Chat memory service — previously stored in ChromaDB.
Now fully migrated to server-side SQL storage (see chat.py and sessions.py).
"""

# Vector memory for chat turns is deprecated in favor of relational SQL memory.
# Do not use add_documents for chat turns anymore.
pass
