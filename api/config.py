"""Application settings, loaded from the environment."""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime configuration.

    Every value comes from the process environment (or a local ``.env``
    file). ``DATABASE_URL`` has no default on purpose: switching between
    Render Postgres and Supabase is a one-variable change.
    """

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str


@lru_cache
def get_settings() -> Settings:
    """Build the settings once and reuse them for the life of the process."""
    return Settings()
