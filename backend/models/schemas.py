from pydantic import BaseModel
from typing import Optional, List, Any
from enum import Enum
from datetime import datetime

class LLMProvider(str, Enum):
    ollama = "ollama"
    openai = "openai"
    anthropic = "anthropic"
    gemini = "gemini"
    groq = "groq"

class LLMConfig(BaseModel):
    provider: LLMProvider
    api_key: Optional[str] = None
    model: Optional[str] = None
    base_url: Optional[str] = None

class DBConfig(BaseModel):
    url: Optional[str] = None  # Direct connection URL
    host: Optional[str] = "localhost"
    port: Optional[int] = 3306
    database: Optional[str] = None 
    username: Optional[str] = None
    password: Optional[str] = None
    db_type: str = "mysql"   # mysql | postgresql | sqlite
    custom_schema: Optional[str] = None  # User provided documentation
    
    @classmethod
    def detect_db_type(cls, db_url: str) -> str:
        if "mysql" in db_url: return "mysql"
        elif "postgresql" in db_url: return "postgres"
        elif "sqlite" in db_url: return "sqlite"
        elif "mssql" in db_url: return "mssql"
        elif "oracle" in db_url: return "oracle"
        return "unknown"

    @property
    def connection_url(self) -> str:
        if self.url:
            return self.url
        if self.db_type == "sqlite":
            return f"sqlite:///{self.database}"

        driver = ""
        if self.db_type == "mysql":
            driver = "mysql+pymysql"
        elif self.db_type in ["postgresql", "postgres"]:
            driver = "postgresql+psycopg2"
        elif self.db_type == "mssql":
            driver = "mssql+pyodbc"
        elif self.db_type == "oracle":
            driver = "oracle+cx_oracle"
        else:
            driver = "mysql+pymysql" # default fallback
            
        return f"{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class ChatMessageBase(BaseModel):
    role: str          # "user" | "assistant"
    content: str
    sql: Optional[str] = None
    data: Optional[Any] = None
    source: Optional[str] = None

class ChatMessage(ChatMessageBase):
    pass

class ChatMessageResponse(ChatMessageBase):
    id: int
    session_id: str
    created_at: datetime

    class Config:
        from_attributes = True

class ChatSessionCreate(BaseModel):
    title: str = "New chat"
    id: Optional[str] = None

class ChatSessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: Optional[datetime] = None
    messages: List[ChatMessageResponse] = []

    class Config:
        from_attributes = True

class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: Optional[int] = 1
    llm_config: Optional[LLMConfig] = None
    history: Optional[List[ChatMessage]] = []  # full conversation history
    session_title: Optional[str] = None        # first user message (for sidebar)

class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    data: Optional[Any] = None
    source: str        # "sql" | "rag" | "general"
    session_id: str
    cached: Optional[bool] = False

class SessionSummary(BaseModel):
    session_id: str
    title: str
    date: str
    message_count: int

class SessionMessagesResponse(BaseModel):
    session_id: str
    title: str
    messages: List[ChatMessage]

class IngestStatus(BaseModel):
    filename: str
    status: str        # "processing" | "done" | "error"
    chunks: int = 0
    message: str = ""

class UserRegistration(BaseModel):
    username: str
    password: str

class TokenRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"

