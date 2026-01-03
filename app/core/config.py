from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings"""

    # Bot Configuration
    BOT_TOKEN: str
    WEBHOOK_URL: str = ""
    WEBHOOK_PATH: str = "/webhook"

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str

    # Air Quality API
    AIR_API_URL: str = "https://api.air.org.kz/api/airgradient/latest"
    AIR_API_RATE_LIMIT: int = 100

    # Application
    DEBUG: bool = False
    LOG_LEVEL: str = "INFO"

    # Data Sync
    SYNC_INTERVAL_MINUTES: int = 5

    # Localization
    DEFAULT_LANGUAGE: str = "ru"
    SUPPORTED_LANGUAGES: list[str] = ["en", "ru", "kk"]

    class Config:
        env_file = ".env"
        case_sensitive = True


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
