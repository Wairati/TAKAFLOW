from functools import lru_cache
#lru_cache in this case is used to cache the settings object so that it is only created once and reused for subsequent calls to get_settings().
#This can improve performance and reduce memory usage, especially if the settings object is expensive to create or if it is accessed frequently.
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration, loaded from environment variables / .env."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "TAKAFLOW API" 
    api_v1_prefix: str = "/api/v1"
    environment: str = "development"

    database_url: str

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7

    cors_origins: list[str] = ["http://localhost:5173", "http://localhost:5174", "http://localhost:5175"]


@lru_cache 
def get_settings() -> Settings: #this is a 
    return Settings()
