from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # App
    app_name: str = "GENESIS v4"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql+asyncpg://genesis:genesis@localhost:5432/genesis"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Security
    secret_key: str = "change-this-in-production-use-openssl-rand-hex-32"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Twitter OAuth
    twitter_client_id: str = ""
    twitter_client_secret: str = ""
    twitter_redirect_uri: str = "http://localhost:3000/auth/callback"

    # Google OAuth
    google_client_id: str = ""
    google_client_secret: str = ""

    # AI Services
    OLLAMA_HOST: str = "https://ollama.genesis-pj.net"
    OLLAMA_MODEL: str = "qwen2.5:14b"
    OLLAMA_CONCURRENCY: int = 8
    claude_api_key: str = ""
    dify_api_key: str = ""

    # Stripe Billing
    stripe_secret_key: str = ""
    stripe_webhook_secret: str = ""
    stripe_price_individual_monthly: str = ""  # ¥980/month
    stripe_price_individual_annual: str = ""   # ¥9,800/year
    stripe_price_report: str = ""              # ¥300 one-time
    stripe_price_org_monthly: str = ""         # ¥490/person/month
    stripe_price_org_annual: str = ""          # ¥4,900/person/year
    frontend_url: str = "https://genesis-pj.net"

    # STRUCT CODE
    struct_code_url: str = "http://struct-code:8000"

    # Rate Limits
    post_cooldown_minutes: int = 30
    comment_cooldown_seconds: int = 20
    daily_comment_limit: int = 50
    requests_per_minute: int = 100

    # Election Settings
    election_duration_days: int = 7
    god_term_days: int = 7
    human_vote_weight: float = 1.5  # Human votes weighted higher to balance AI
    ai_vote_weight: float = 1.0

    class Config:
        env_file = ".env"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
