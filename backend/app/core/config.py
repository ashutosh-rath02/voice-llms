from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables.

    Every field can be overridden by an env var of the same (upper-cased) name,
    e.g. DATABASE_URL. In local dev the values come from backend/.env; in
    staging/production they come from the platform's secret store.
    """

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "voiceai-backend"
    app_env: str = "dev"  # dev | staging | prod
    log_level: str = "INFO"

    # Comma-separated browser origins allowed to call this API (CORS).
    # Staging adds the Vercel URL, e.g. "https://voiceai-web.vercel.app".
    cors_origins: str = "http://localhost:3000"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    database_url: str = "postgresql+asyncpg://voiceai:voiceai_dev@localhost:5432/voiceai"
    redis_url: str = "redis://localhost:6379/0"

    # External checks (readiness probes, provider pings) must never hang the
    # event loop; everything network-facing gets an explicit timeout.
    health_check_timeout_seconds: float = 2.0

    # Auth. The default secret only exists so local dev works out of the box;
    # staging/prod MUST override JWT_SECRET (rotating it invalidates all tokens).
    jwt_secret: str = "dev-only-secret-change-me"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    # Dev admin created by the seed script; override both in any shared env.
    seed_admin_email: str = "admin@voiceai.local"
    seed_admin_password: str = "admin-dev-password"

    # Realtime voice providers. Values live in backend/.env (gitignored) locally
    # and in the platform secret store when deployed. Empty string = not
    # configured; the voice endpoints return 503 rather than failing cryptically.
    livekit_url: str = ""
    livekit_api_key: str = ""
    livekit_api_secret: str = ""
    deepgram_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    elevenlabs_api_key: str = ""


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide Settings instance (parsed once, then cached)."""
    return Settings()
