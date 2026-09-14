from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent.parent
    PROJECT_NAME: str = "Finance Multimodal RAG + MCP"

    DOCUMENTS_DIR: Path = BASE_DIR / "shared" / "documents"

    REDIS_URL: str = "redis://127.0.0.1:6379/0"
    CELERY_BROKER_URL: str = "redis://127.0.0.1:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://127.0.0.1:6379/2"

    OLLAMA_URL: str = "http://localhost:11434"
    OLLAMA_VISION_MODEL: str = "llava:7b-v1.6"
    OLLAMA_LLM_MODEL: str = "qwen2.5:7b"
    OLLAMA_EMBEDDING_MODEL: str = "nomic-embed-text"

    DATABASE_NAME: str = "localdb"
    DATABASE_USER: str = "postgres"
    DATABASE_PASSWORD: str = "toor"
    DATABASE_HOST: str = "localhost"
    DATABASE_PORT: int = 5432

    AUTH_ALGORITHM: str = "HS256"
    SIGNING_KEY: str = "change-me-in-local-env"
    TOKEN_EXPIRY: int = 24

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=True,
    )

    @property
    def DATABASE_URL(self) -> str:
        user = quote_plus(self.DATABASE_USER)
        password = quote_plus(self.DATABASE_PASSWORD)
        return (
            f"postgresql+psycopg://{user}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
