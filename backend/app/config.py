from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://genesis:genesis@db:5432/genesis"
    DATABASE_URL_SYNC: str = "postgresql://genesis:genesis@db:5432/genesis"
    REDIS_URL: str = "redis://redis:6379/0"

    # Claude API
    ANTHROPIC_API_KEY: str = ""
    CLAUDE_MODEL: str = "claude-opus-4-20250514"

    # Ollama
    OLLAMA_HOST: str = "http://host.docker.internal:11434"
    OLLAMA_MODEL: str = "llama3.1:8b"

    # Server
    SECRET_KEY: str = "change-this-to-a-random-secret-key"
    DEBUG: bool = True
    CORS_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # World Settings
    INITIAL_AI_COUNT: int = 0
    MAX_AI_COUNT: int = 1000
    TICK_INTERVAL_MS: int = 1000
    AI_THINKING_INTERVAL_MS: int = 3000

    # Admin Auth
    ADMIN_USERNAME: str = "admin"
    ADMIN_PASSWORD: str = "change-this-password"

    # Translation
    DEEPL_API_KEY: Optional[str] = None

    @property
    def cors_origins_list(self) -> list[str]:
        return [origin.strip() for origin in self.CORS_ORIGINS.split(",")]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
