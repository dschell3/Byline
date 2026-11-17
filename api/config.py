"""Application settings, loaded from the environment."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every value comes from the process environment (or a local ``.env``
    file). ``DATABASE_URL`` has no default on purpose: switching between
    Render Postgres and Supabase is a one-variable change.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str

    # File storage (SCRUM-83). ``local`` writes to a directory on this machine
    # for development and CI; ``r2`` is Cloudflare R2 through its S3 API.
    # The four R2 values are Render env vars; .env.example lists them blank.
    storage_backend: Literal["local", "r2"] = "local"
    local_storage_dir: str | None = None
    r2_endpoint: str | None = None
    r2_bucket: str | None = None
    r2_access_key_id: str | None = None
    r2_secret_access_key: str | None = None


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them for the life of the process."""
    return Settings()
