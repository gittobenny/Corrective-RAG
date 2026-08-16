# Environment-backed application configuration.

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
import os

from dotenv import load_dotenv


PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env", override=False)


def _as_bool(name: str, default: bool = False) -> bool:
    return os.getenv(name, str(default)).lower() in {"1", "true", "yes", "on"}


def _as_csv(name: str, default: str) -> tuple[str, ...]:
    return tuple(value.strip() for value in os.getenv(name, default).split(",") if value.strip())


@dataclass(frozen=True)
class Settings:
    cors_origins: tuple[str, ...] = _as_csv(
        "CORS_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    )
    upload_root: Path = Path(os.getenv("UPLOAD_ROOT", PROJECT_ROOT / "uploads"))
    metadata_db_path: Path = Path(
        os.getenv("METADATA_DB_PATH", PROJECT_ROOT / "data" / "documents.sqlite3")
    )
    max_upload_bytes: int = int(os.getenv("MAX_UPLOAD_BYTES", 25 * 1024 * 1024))
    default_collection_id: str = os.getenv("DEFAULT_COLLECTION_ID", "default")

    celery_broker_url: str = os.getenv(
        "CELERY_BROKER_URL", "redis://localhost:6379/0"
    )
    celery_result_backend: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://localhost:6379/1"
    )

    weaviate_http_host: str = os.getenv("WEAVIATE_HTTP_HOST", "localhost")
    weaviate_http_port: int = int(os.getenv("WEAVIATE_HTTP_PORT", "8080"))
    weaviate_http_secure: bool = _as_bool("WEAVIATE_HTTP_SECURE")
    weaviate_grpc_host: str = os.getenv("WEAVIATE_GRPC_HOST", "localhost")
    weaviate_grpc_port: int = int(os.getenv("WEAVIATE_GRPC_PORT", "50051"))
    weaviate_grpc_secure: bool = _as_bool("WEAVIATE_GRPC_SECURE")
    weaviate_collection: str = os.getenv("WEAVIATE_COLLECTION", "DocumentChunk")

    embedding_model: str = os.getenv(
        "EMBEDDING_MODEL", "sentence-transformers/all-MiniLM-L6-v2"
    )
    chunk_size: int = int(os.getenv("CHUNK_SIZE", "800"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "100"))

    groq_api_key: str | None = os.getenv("GROQ_API_KEY")
    groq_model: str = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
    tavily_api_key: str | None = os.getenv("TAVILY_API_KEY")
    retrieval_limit: int = int(os.getenv("RETRIEVAL_LIMIT", "8"))
    retrieval_max_distance: float = float(
        os.getenv("RETRIEVAL_MAX_DISTANCE", "0.65")
    )
    web_search_results: int = int(os.getenv("WEB_SEARCH_RESULTS", "3"))


@lru_cache
def get_settings() -> Settings:
    settings = Settings()
    settings.upload_root.mkdir(parents=True, exist_ok=True)
    settings.metadata_db_path.parent.mkdir(parents=True, exist_ok=True)
    return settings
