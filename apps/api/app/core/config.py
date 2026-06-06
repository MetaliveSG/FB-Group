"""Application configuration via environment variables (12-factor)."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- App ---
    APP_NAME: str = "FB Group F&B Platform API"
    ENV: str = "local"  # local | docker | staging | prod
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # --- Database ---
    # SQLite for dev/tests (zero-setup, runs anywhere). Postgres in Docker/prod.
    DATABASE_URL: str = "sqlite:///./fbgroup.db"

    # --- Auth / JWT ---
    JWT_SECRET: str = "dev-secret-change-me-in-production"
    JWT_ALG: str = "HS256"
    # Dedicated key for encrypting owner-revealable POS PINs at rest (Fernet). Falls back to
    # JWT_SECRET so dev/docker need no extra config; set a distinct value (or KMS) in production.
    PIN_SECRET: str | None = None
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # --- OTP (mock provider) ---
    OTP_TTL_SECONDS: int = 300
    OTP_LENGTH: int = 6
    OTP_MAX_ATTEMPTS: int = 5

    # --- Rate limiting (simple in-process token buckets for PoC) ---
    RATE_LIMIT_OTP_PER_MIN: int = 5
    RATE_LIMIT_LOGIN_PER_MIN: int = 10

    # --- SG F&B money rules (mock) ---
    GST_RATE: float = 0.09          # Singapore GST 9%
    SERVICE_CHARGE_RATE: float = 0.10  # typical 10% service charge

    # --- CORS ---
    CORS_ORIGINS: str = "http://localhost:3000,http://127.0.0.1:3000"

    # --- WhatsApp mock ---
    WHATSAPP_PROVIDER: str = "mock"  # mock | twilio | meta

    # --- AI insights (Claude / Anthropic) ---
    # Off by default: the advisor runs a deterministic, rule-based fallback so the
    # PoC works (and tests stay reproducible) with no API key / network. Set
    # AI_ENABLED=1 + ANTHROPIC_API_KEY=... to switch the same endpoint to Claude.
    AI_ENABLED: bool = False
    ANTHROPIC_API_KEY: str = ""
    AI_MODEL: str = "claude-opus-4-7"
    AI_MAX_TOKENS: int = 4096
    AI_TIMEOUT_SECONDS: float = 30.0

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.CORS_ORIGINS.split(",") if o.strip()]

    @property
    def ai_ready(self) -> bool:
        """True when a live Claude call is both enabled and credentialed."""
        return bool(self.AI_ENABLED and self.ANTHROPIC_API_KEY)


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
