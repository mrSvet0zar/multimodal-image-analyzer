"""Typed, validated application configuration (pydantic-settings).

Single source of truth for config — reads environment variables and a local
`.env` file. Import `settings` anywhere instead of scattering `os.getenv`.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

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
    db_path: str = "./analyses.db"

    # --- HTTP / limits ---
    cors_origins: str = "http://localhost:5173"
    rate_limit_max: int = 30
    rate_limit_window: int = 60

    # --- Logging ---
    log_level: str = "INFO"

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def models(self) -> list[str]:
        """Primary model followed by any configured fallback."""
        chain = [self.vision_model]
        if self.vision_fallback_model:
            chain.append(self.vision_fallback_model)
        return chain


settings = Settings()
