import os
from typing import List
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator

class Settings(BaseSettings):
    PROJECT_NAME: str = "upay Pulse"
    PROJECT_TYPE: str = "AI-powered MFS Intelligence Ecosystem"
    VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    @field_validator("DEBUG", mode="before")
    @classmethod
    def parse_debug(cls, v):
        if isinstance(v, bool):
            return v
        s = str(v).strip().lower()
        return s in ("1", "true", "yes", "on")

    # Security
    SECRET_KEY: str = "upay_pulse_super_secure_demo_secret_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 120

    # Databases
    DATABASE_URL: str = "postgresql+psycopg2://postgres:@localhost:5432/upay_pulse"
    SQLITE_FALLBACK_URL: str = "sqlite:///./upay_pulse.db"

    # Event Bus / Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    USE_REDIS_FALLBACK: bool = True

    # Risk Engine
    RISK_THRESHOLD_LOW: float = 0.40
    RISK_THRESHOLD_HIGH: float = 0.75

    # AI & Voice Coach
    AI_PROVIDER: str = "mock"  # "gemini", "openai", "mock"
    GEMINI_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # CORS — stored as comma-separated string to avoid pydantic-settings JSON parsing issues
    CORS_ORIGINS: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,https://*.onrender.com"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v):
        if isinstance(v, list):
            return ",".join(v)
        if isinstance(v, str) and v.strip().startswith("["):
            import json
            try:
                parsed = json.loads(v)
                return ",".join(parsed)
            except Exception:
                pass
        return v or "http://localhost:5173"

    @property
    def cors_origins_list(self) -> List[str]:
        return [i.strip() for i in self.CORS_ORIGINS.split(",") if i.strip()]

    # Latency limits
    FREEZE_MAX_TIMEOUT_MS: int = 300

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_ignore_empty=True,
        extra="ignore"
    )

settings = Settings()
