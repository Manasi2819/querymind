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
    host: str
    port: int = 5432
    database: str
    username: str
    password: str
    db_type: str = "postgresql"   # postgresql | mysql | sqlite

    @property
    def connection_url(self) -> str:
        if self.db_type == "sqlite":
            return f"sqlite:///{self.database}"
        driver = "postgresql" if self.db_type == "postgresql" else "mysql+pymysql"
        return f"{driver}://{self.username}:{self.password}@{self.host}:{self.port}/{self.database}"

class ChatMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str

class ChatRequest(BaseModel):
    message: str
    session_id: str
    llm_config: Optional[LLMConfig] = None

class ChatResponse(BaseModel):
    answer: str
    source: str        # "sql" | "rag" | "general"
    session_id: str

class IngestStatus(BaseModel):
    filename: str
    status: str        # "processing" | "done" | "error"
    chunks: int = 0
    message: str = ""

class TokenRequest(BaseModel):
    username: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
