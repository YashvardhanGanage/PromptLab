import os
from pathlib import Path
from pydantic import BaseModel

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

def _parse_cors_origins(raw_origins: str | None) -> list[str]:
    """Parse comma-separated CORS origins from environment, defaulting to local dev ports."""
    if not raw_origins:
        return [
            "http://localhost:5173",
            "http://127.0.0.1:5173",
            "http://localhost:3000",
            "http://127.0.0.1:3000"
        ]
    return [origin.strip() for origin in raw_origins.split(",") if origin.strip()]

class Settings(BaseModel):
    DATABASE_PATH: str = os.getenv("DATABASE_PATH", str(BASE_DIR / "promptlab.db"))
    OLLAMA_BASE_URL: str = os.getenv("OLLAMA_BASE_URL", "http://127.0.0.1:11434")
    DEFAULT_MODEL: str = os.getenv("DEFAULT_MODEL", "llama3.2:1b")
    MOCK_LLM: bool = os.getenv("MOCK_LLM", "true").lower() in ("true", "1", "yes")
    CORS_ORIGINS: list[str] = _parse_cors_origins(os.getenv("CORS_ORIGINS"))
    DATA_DIR: Path = DATA_DIR

settings = Settings()
