from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    database_url: str = "postgresql+psycopg://continuity:continuity@db:5432/continuity"
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-3.6-flash-lite"
    intent_extractor: Literal["mock", "gemini"] = "mock"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
