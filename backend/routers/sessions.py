from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
import uuid

from database import get_db
from models import db_models as models
from models import schemas

router = APIRouter(prefix="/sessions", tags=["sessions"])

@router.get("", response_model=List[schemas.ChatSessionResponse])
def get_sessions(user_id: int = 1, db: Session = Depends(get_db)):
    """Retrieve all chat sessions for the user, ordered by most recently updated."""
    sessions = db.query(models.ChatSession)\
                 .filter(models.ChatSession.user_id == user_id)\
                 .order_by(models.ChatSession.updated_at.desc())\
                 .all()
    return sessions

@router.post("", response_model=schemas.ChatSessionResponse)
def create_session(session_in: schemas.ChatSessionCreate, user_id: int = 1, db: Session = Depends(get_db)):
    """Create a new chat session."""
    session_id = session_in.id if session_in.id else str(uuid.uuid4())
    
    db_session = models.ChatSession(
        id=session_id,
        user_id=user_id,
        title=session_in.title
    )
    db.add(db_session)
    db.commit()
    db.refresh(db_session)
    return db_session

@router.get("/{session_id}", response_model=schemas.ChatSessionResponse)
def get_session(session_id: str, user_id: int = 1, db: Session = Depends(get_db)):
    """Get a specific session with its messages."""
    session = db.query(models.ChatSession)\
                .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user_id)\
                .first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session

@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_session(session_id: str, user_id: int = 1, db: Session = Depends(get_db)):
    """Delete a specific session."""
    session = db.query(models.ChatSession)\
                .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user_id)\
                .first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    db.delete(session)
    db.commit()
    return None

@router.patch("/{session_id}", response_model=schemas.ChatSessionResponse)
def update_session_title(session_id: str, title: str, user_id: int = 1, db: Session = Depends(get_db)):
    """Update a session's title."""
    session = db.query(models.ChatSession)\
                .filter(models.ChatSession.id == session_id, models.ChatSession.user_id == user_id)\
                .first()
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.title = title
    db.commit()
    db.refresh(session)
    return session
