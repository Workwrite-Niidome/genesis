from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://genesis:genesis@db:5432/genesis"
    DATABASE_URL_SYNC: str = "postgresql://genesis:genesis@db:5432/genesis"
    REDIS_URL: str = "redis://redis:6379/0"

    # Claude API
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_OPUS_MODEL: str = "claude-opus-4-20250514"
    CLAUDE_HAIKU_MODEL: str = "claude-haiku-4-5-20251001"
    CLAUDE_MODEL: str = "claude-opus-4-20250514"  # backward compat

    # Ollama
    OLLAMA_HOST: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"
    OLLAMA_CONCURRENCY: int = 4
    OLLAMA_NUM_GPU: int = -1
    OLLAMA_NUM_PREDICT: int = 512

    # Server
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    DEBUG: bool = False
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"
    GUNICORN_WORKERS: int = 2

    # World Settings (v3)
    INITIAL_NATIVE_AI_COUNT: int = 0
    MAX_ENTITIES_PER_INSTANCE: int = 100
    TICK_INTERVAL_MS: int = 1000
    AI_THINKING_INTERVAL_MS: int = 10000

    # Legacy (backward compat)
    INITIAL_AI_COUNT: int = 0
    MAX_AI_COUNT: int = 1000

    # Admin Auth
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this-password"

    # Claude API Budget
    CLAUDE_DAILY_BUDGET_USD: float = 5.0
    CLAUDE_COST_TRACKING: bool = True

    # User Agents
    MAX_AGENTS_PER_USER_FREE: int = 1
    MAX_AGENTS_PER_USER_PREMIUM: int = 5

    # Translation
    DEEPL_API_KEY: Optional[str] = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
