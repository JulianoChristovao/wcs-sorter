"""
Configurações centralizadas da aplicação WCS.
"""
from functools import lru_cache
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Aplicação
    APP_NAME: str = "WCS Sorter"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    API_PREFIX: str = "/api/v1"

    # Banco de dados
    DATABASE_URL: str = "postgresql+asyncpg://wcs_user:wcs_secret@db:5432/wcs_db"
    DATABASE_URL_SYNC: str = "postgresql://wcs_user:wcs_secret@db:5432/wcs_db"

    # Segurança
    SECRET_KEY: str = "CHANGE-THIS-IN-PRODUCTION-use-openssl-rand-hex-32"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 480  # 8 horas

    # Integração WMS
    WMS_WEBHOOK_URL: Optional[str] = None
    WMS_API_KEY: Optional[str] = None
    WMS_TIMEOUT_SECONDS: int = 10

    # Sorter (API machine-to-machine)
    SORTER_API_KEY: Optional[str] = "sorter-api-key-change-me"

    # CORS
    CORS_ORIGINS: list[str] = ["http://localhost:3000", "http://localhost:5173", "http://127.0.0.1:5173"]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()