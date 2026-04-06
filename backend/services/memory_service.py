"""
Chat memory service — stores and retrieves conversation history per session.
Each turn is stored in ChromaDB under a session-specific collection.
"""

import uuid
from datetime import datetime
from services.embed_service import add_documents, similarity_search

def save_turn(session_id: str, role: str, content: str):
    """Saves a single chat turn to vector memory."""
    add_documents(
        texts=[content],
        metadatas=[{
            "session_id": session_id,
            "role": role,
            "timestamp": datetime.utcnow().isoformat(),
            "turn_id": str(uuid.uuid4()),
        }],
        collection_name=f"memory_{session_id}",
    )

def get_relevant_history(session_id: str, query: str, k: int = 4) -> str:
    """Returns recent relevant chat history as a formatted string."""
    try:
        results = similarity_search(query, f"memory_{session_id}", k=k)
        if not results:
            return ""
        history = "\n".join(
            f"[{r.metadata.get('role','?')}] {r.page_content}"
            for r in results
        )
        return f"Relevant conversation history:\n{history}\n"
    except Exception:
        return ""
