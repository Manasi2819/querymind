from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    # LLM
    llm_provider: str = "ollama"           # "ollama" | "openai" | "anthropic"
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi3:mini"
    ollama_embed_model: str = "nomic-embed-text"
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-haiku-20240307"

    # Database
    postgres_host: str = "localhost"
    postgres_port: int = 5432
    postgres_db: str = "querymind"
    postgres_user: str = "querymind_user"
    postgres_password: str = "changeme"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Auth
    jwt_secret_key: str = "change_this"
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Files
    upload_dir: str = "./uploads"

    # Admin
    admin_username: str = "admin"
    admin_password: str = "admin123"

    class Config:
        env_file = (".env", "../.env")

    @property
    def postgres_url(self) -> str:
        return (
            f"postgresql://{self.postgres_user}:{self.postgres_password}"
            f"@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"
        )

@lru_cache
def get_settings() -> Settings:
    return Settings()
