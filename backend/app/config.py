"""Typed, validated application configuration (pydantic-settings).

Single source of truth for config — reads environment variables and a local
`.env` file. Import `settings` anywhere instead of scattering `os.getenv`.
"""

from pydantic import AliasChoices, Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- Anthropic / Vision ---
    anthropic_api_key: str = ""
    vision_model: str = "claude-sonnet-5"
    # Optional model to try if the primary is overloaded/unavailable.
    vision_fallback_model: str = ""
    request_timeout: float = 60.0
    max_retries: int = 3

    # --- Pricing (USD per million tokens) for cost estimation ---
    # Claude Sonnet 5 standard rates; override via env if they change.
    price_per_mtok_input: float = 3.0
    price_per_mtok_output: float = 15.0

    # --- Uploads / storage ---
    max_file_size: int = 10 * 1024 * 1024
    upload_dir: str = "./uploads"

    # --- Database ---
    # SQLite by default (dev/tests); set DATABASE_URL to a Postgres URL in prod.
    database_url: str = "sqlite+aiosqlite:///./analyses.db"

    # --- Object storage (S3 / Cloudflare R2) ---
    # If s3_bucket is set, images go to S3/R2; otherwise to the local filesystem.
    s3_bucket: str = ""
    s3_endpoint_url: str = ""  # e.g. https://<account>.r2.cloudflarestorage.com
    s3_region: str = "auto"
    # Accept both S3_ACCESS_KEY_ID and the shorter S3_ACCESS_KEY people often set.
    s3_access_key_id: str = Field(
        default="",
        validation_alias=AliasChoices("s3_access_key_id", "s3_access_key"),
    )
    s3_secret_access_key: str = Field(
        default="",
        validation_alias=AliasChoices("s3_secret_access_key", "s3_secret_key"),
    )

    # --- HTTP / limits ---
    api_port: int = 8000
    cors_origins: str = "http://localhost:5173"
    rate_limit_max: int = 30
    rate_limit_window: int = 60

    # Distributed rate limit + shared cost guard (falls back to in-memory if unset).
    redis_url: str = ""
    # Global daily spend cap in USD; 0 disables the guard.
    daily_cost_limit_usd: float = 0.0

    # --- Logging / error tracking ---
    log_level: str = "INFO"
    sentry_dsn: str = ""
    environment: str = "production"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def async_database_url(self) -> str:
        """Normalize the DB URL to an async driver (Railway gives postgresql://)."""
        url = self.database_url
        if url.startswith("postgres://"):
            url = url.replace("postgres://", "postgresql+asyncpg://", 1)
        elif url.startswith("postgresql://"):
            url = url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return url

    @property
    def models(self) -> list[str]:
        """Primary model followed by any configured fallback."""
        chain = [self.vision_model]
        if self.vision_fallback_model:
            chain.append(self.vision_fallback_model)
        return chain


settings = Settings()
