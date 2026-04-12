from sqlalchemy import Column, Integer, String, JSON, ForeignKey, DateTime, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base


class AdminUser(Base):
    __tablename__ = "admin_users"

    id            = Column(Integer, primary_key=True, index=True)
    username      = Column(String(255), unique=True, index=True, nullable=False)
    password_hash = Column(String(255), nullable=False)

    # Relationships
    settings = relationship("AdminSettings", back_populates="owner", uselist=False)
    sessions = relationship("ChatSession", back_populates="owner")


class AdminSettings(Base):
    __tablename__ = "admin_settings"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("admin_users.id"), unique=True)

    # Store settings as JSON bundles
    db_config  = Column(JSON, default={})
    llm_config = Column(JSON, default={})
    api_keys   = Column(JSON, default={})

    owner = relationship("AdminUser", back_populates="settings")


class UploadedFile(Base):
    __tablename__ = "uploaded_files"

    id          = Column(Integer, primary_key=True, index=True)
    user_id     = Column(Integer, ForeignKey("admin_users.id"), index=True)
    filename    = Column(String(512), index=True)
    file_type   = Column(String(64))   # 'document' or 'knowledge_base'
    source_type = Column(String(16))   # 'json', 'csv', 'sql'
    upload_date = Column(String(64))
    chunk_count = Column(Integer, default=0)


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id         = Column(String(128), primary_key=True, index=True)  # UUID or frontend-generated
    user_id    = Column(Integer, ForeignKey("admin_users.id"), index=True)
    title      = Column(String(512), default="New chat")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    owner    = relationship("AdminUser", back_populates="sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id         = Column(Integer, primary_key=True, index=True)
    session_id = Column(String(128), ForeignKey("chat_sessions.id", ondelete="CASCADE"), index=True)
    role       = Column(String(32))     # 'user' or 'assistant'
    content    = Column(Text)           # Use Text for long messages (no length limit)
    sql        = Column(Text,      nullable=True)
    data       = Column(JSON,      nullable=True)
    source     = Column(String(64), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    session = relationship("ChatSession", back_populates="messages")
