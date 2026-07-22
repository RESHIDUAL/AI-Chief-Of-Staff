import os
from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Ensure .env is loaded from project root
ENV_PATH = Path(__file__).resolve().parent.parent.parent / ".env"


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Lyzr SDK
    LYZR_AGENT_API_KEY: str = "sk-default-bQDp4vxgOlyrbqJhspDu34f1XfIPjSWB"
    LYZR_EXTRACTION_AGENT_ID: str = "6a5f492111fc9a484e9584bb"
    LYZR_RAG_AGENT_ID: str = "6a5f4bfe7976aaac9b9a5f2b"

    # Qdrant
    QDRANT_URL: str = "http://localhost:6333"
    QDRANT_API_KEY: str | None = None
    QDRANT_COLLECTION_NAME: str = "org_memory"
    QDRANT_GRPC_PORT: int = 6334
    QDRANT_PREFER_GRPC: bool = True

    # PostgreSQL
    POSTGRES_USER: str = "chiefofstaff"
    POSTGRES_PASSWORD: str = "chiefofstaff"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "org_memory"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    # Embeddings
    EMBED_MODEL_NAME: str = "all-MiniLM-L6-v2"
    EMBED_DIM: int = 384

    # Auth / OAuth
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    JWT_SECRET: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRY_MINUTES: int = 60

    # RBAC Role Resolution
    RBAC_MODE: str = "static"  # "static" (ROLE_TABLE lookup) or "workspace_groups" (Admin SDK)
    ROLE_TABLE: str = "{}"     # JSON map of email -> role, e.g. '{"admin@co.com":"admin"}'
    GOOGLE_APPLICATION_CREDENTIALS: str = ""
    GOOGLE_ADMIN_IMPERSONATE_EMAIL: str = ""
    LEADERSHIP_GROUP_EMAIL: str = ""

    # Google Drive & Pub/Sub Integration
    GOOGLE_DRIVE_FOLDER_ID: str = ""
    GOOGLE_PUBSUB_PROJECT_ID: str = ""
    GOOGLE_PUBSUB_TOPIC: str = "meeting-transcripts"

    # App
    APP_ENV: str = "development"
    APP_DEBUG: bool = True
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000
    CORS_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://localhost:5173",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
        "*",
    ]

    class Config:
        env_file = str(ENV_PATH)
        env_file_encoding = "utf-8"
        extra = "ignore"


@lru_cache()
def get_settings() -> Settings:
    """Cached settings singleton."""
    return Settings()


settings = get_settings()
