"""
Configuration settings for TaskTimer Cloud.
"""

from pydantic_settings import BaseSettings
from typing import List, Union


class Settings(BaseSettings):
    """Application settings."""

    # Database
    mongodb_url: str = "mongodb://localhost:27017"
    database_name: str = "tasktimer"

    # Security
    secret_key: str = "your-secret-key-change-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 10080  # 7 days

    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: Union[str, List[str]] = "*"

    # Session Configuration
    default_session_expiry_hours: int = 24

    class Config:
        env_file = ".env"
        case_sensitive = False

    @property
    def cors_origins_list(self) -> List[str]:
        """Get CORS origins as a list."""
        if isinstance(self.cors_origins, str):
            if self.cors_origins == "*":
                return ["*"]
            return [origin.strip() for origin in self.cors_origins.split(",")]
        return self.cors_origins


settings = Settings()
