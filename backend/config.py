from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # ── LLM ───────────────────────────────────────────────────────────────
    llm_provider: str = "openai"           # "endpoint" | "openai" | "anthropic" | "gemini" | "groq"
    endpoint_base_url: str = ""
    endpoint_model: str = ""
    endpoint_api_key: str = ""
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-3-5-haiku-20241022"
    gemini_api_key: str = ""
    gemini_model: str = "gemini-1.5-flash"
    groq_api_key: str = ""
    groq_model: str = "llama3-8b-8192"

    # ── Database (single URL — database-agnostic) ─────────────────────────
    # Supports SQLite | MySQL | PostgreSQL via DATABASE_URL.
    # The backend auto-creates the target database on startup.
    # Override via DATABASE_URL environment variable or .env file.
    database_url: str = "sqlite:///./querymind_metadata.db"

    # Redis removed as it is not actively used used for caching or sessions
    # ── Auth ──────────────────────────────────────────────────────────────
    jwt_secret_key: str = ""
    jwt_algorithm: str = "HS256"
    jwt_expire_minutes: int = 1440
    fernet_key: str = ""

    # ── ChromaDB ──────────────────────────────────────────────────────────
    chroma_persist_dir: str = "../chroma_db"

    # ── File uploads ──────────────────────────────────────────────────────
    upload_dir: str = "./uploads"

    # ── Admin credentials ─────────────────────────────────────────────────
    admin_username: str = ""
    admin_password: str = ""

    # ── Infrastructure Credentials ────────────────────────────────────────
    postgres_password: str = "changeme"
    hf_token: str = ""

    class Config:
        env_file = (".env", "../.env")
        extra = "ignore"


@lru_cache
def get_settings() -> Settings:
    return Settings()
