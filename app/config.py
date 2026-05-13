from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    google_client_id: str
    google_client_secret: str
    google_redirect_uri: str

    supabase_url: str
    supabase_service_key: str

    secret_key: str
    frontend_url: str = "http://localhost:3000"
    environment: str = "development"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()
