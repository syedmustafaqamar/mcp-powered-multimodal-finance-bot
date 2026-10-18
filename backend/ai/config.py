from functools import lru_cache
from pathlib import Path
from urllib.parse import quote_plus

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    BASE_DIR: Path = Path(__file__).resolve().parent.parent

    PROMPTS_DIR: Path = BASE_DIR / "ai" / "prompts"
    DOCUMENTS_DIR: Path = BASE_DIR / "shared" / "documents"
    CHROMA_DIR: Path = BASE_DIR / "shared" / "chroma"

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

    CHROMA_COLLECTION: str = "documents"
    CHUNK_SIZE: int = 1800
    CHUNK_OVERLAP: int = 200
    RETRIEVAL_TOP_K: int = 5

    MCP_HOST: str = "127.0.0.1"
    MCP_PORT: int = 8001

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
            f"postgresql://{user}:{password}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
settings.DOCUMENTS_DIR.mkdir(parents=True, exist_ok=True)
settings.CHROMA_DIR.mkdir(parents=True, exist_ok=True)
