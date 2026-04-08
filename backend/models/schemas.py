from pydantic import BaseModel
from typing import Optional, List
from enum import Enum

class LLMProvider(str, Enum):
    ollama = "ollama"
    openai = "openai"
    anthropic = "anthropic"

class LLMConfig(BaseModel):
    provider: LLMProvider
    api_key: Optional[str] = None
    model: Optional[str] = None

class DBConfig(BaseModel):
    url: Optional[str] = None  # Direct connection URL
    host: Optional[str] = "localhost"
    port: Optional[int] = 3306
    database: Optional[str] = None 
    username: Optional[str] = None
    password: Optional[str] = None
    db_type: str = "mysql"   # mysql | postgresql | sqlite
    custom_schema: Optional[str] = None  # User provided documentation
    
    @property
    def connection_url(self) -> str:
        if self.url:
            return self.url
        if self.db_type == "sqlite":
            return f"sqlite:///{self.database}"
        driver = "mysql+pymysql" if self.db_type == "mysql" else "postgresql"
        return f"{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class ChatMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str
    user_id: Optional[int] = 1 # Default to 1 for backward compatibility
    llm_config: Optional[LLMConfig] = None

class ChatResponse(BaseModel):
    answer: str
    sql: Optional[str] = None
    data: Optional[List[dict]] = None
    source: str        # "sql" | "rag" | "general"
    session_id: str

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
