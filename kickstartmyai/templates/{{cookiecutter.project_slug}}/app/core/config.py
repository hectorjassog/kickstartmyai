"""Application configuration and settings."""

import os
from typing import List, Optional, Dict, Any, Union
from pydantic import BaseModel, AnyHttpUrl, field_validator, model_validator
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings."""
    
    # Basic app configuration
    PROJECT_NAME: str = "{{cookiecutter.project_name}}"
    PROJECT_SLUG: str = "{{cookiecutter.project_slug}}"
    VERSION: str = "{{cookiecutter.version}}"
    DESCRIPTION: str = "{{cookiecutter.project_description}}"
    DEBUG: bool = False
    API_V1_STR: str = "/api/v1"
    
    # Server Configuration
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    RELOAD: bool = False
    
    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 8  # 8 days
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 30  # 30 days
    
    # Database
    DATABASE_URL: Optional[str] = None
    POSTGRES_SERVER: str = "localhost"
    POSTGRES_USER: str = "{{cookiecutter.database_user}}"
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = "{{cookiecutter.database_name}}"
    POSTGRES_PORT: str = "5432"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    CREATE_TABLES_ON_STARTUP: bool = True
    
    @model_validator(mode="after")
    def assemble_db_connection(self) -> "Settings":
        if self.DATABASE_URL is None:
            self.DATABASE_URL = f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}@{self.POSTGRES_SERVER}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        return self
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_POOL_SIZE: int = 10
    REDIS_TTL_DEFAULT: int = 3600  # 1 hour
    
    # Cache Configuration
    CACHE_ENABLED: bool = True
    CACHE_PREFIX: str = "{{cookiecutter.project_slug}}"
    CACHE_DEFAULT_TTL: int = 300  # 5 minutes
    
    # CORS
    BACKEND_CORS_ORIGINS: List[AnyHttpUrl] = []
    
    @field_validator("BACKEND_CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        elif isinstance(v, list):
            return v
        elif isinstance(v, str):
            return [v]
        raise ValueError(v)

    # AI Provider Settings
    OPENAI_API_KEY: Optional[str] = None
    OPENAI_ORG_ID: Optional[str] = None
    OPENAI_MODEL_DEFAULT: str = "gpt-4"
    OPENAI_MAX_TOKENS: int = 4096
    OPENAI_TEMPERATURE: float = 0.7
    
    ANTHROPIC_API_KEY: Optional[str] = None
    ANTHROPIC_MODEL_DEFAULT: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS: int = 4096
    
    GEMINI_API_KEY: Optional[str] = None
    GEMINI_MODEL_DEFAULT: str = "gemini-1.5-flash"
    GEMINI_MAX_TOKENS: int = 4096
    GEMINI_TEMPERATURE: float = 0.7
    
    # AI Service Configuration
    AI_REQUEST_TIMEOUT: int = 60
    AI_MAX_RETRIES: int = 3
    AI_RETRY_DELAY: float = 1.0
    AI_BATCH_SIZE: int = 10
    
    # Function Calling Configuration
    FUNCTION_CALLING_ENABLED: bool = True
    MAX_FUNCTION_CALLS: int = 5
    FUNCTION_TIMEOUT: int = 30
    
    # Tool Configuration
    TOOLS_ENABLED: bool = True
    WEB_SEARCH_MAX_RESULTS: int = 10
    CODE_EXECUTION_TIMEOUT: int = 30
    FILE_UPLOAD_MAX_SIZE: int = 10 * 1024 * 1024  # 10MB
    
    # Monitoring & Logging
    SENTRY_DSN: Optional[str] = None
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    LOG_FILE: Optional[str] = None
    LOG_SAMPLING_RATE: float = 1.0  # 1.0 = log all, 0.1 = log 10%
    
    # Metrics & Telemetry
    METRICS_ENABLED: bool = True
    TELEMETRY_ENABLED: bool = True
    PROMETHEUS_METRICS: bool = False
    
    # AWS Settings
    AWS_REGION: str = "{{cookiecutter.aws_region}}"
    AWS_ACCESS_KEY_ID: Optional[str] = None
    AWS_SECRET_ACCESS_KEY: Optional[str] = None
    AWS_S3_BUCKET: Optional[str] = None
    
    # Rate limiting
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_REQUESTS_PER_MINUTE: int = 60
    RATE_LIMIT_BURST_SIZE: int = 100
    
    # Background Tasks
    CELERY_BROKER_URL: Optional[str] = None
    CELERY_RESULT_BACKEND: Optional[str] = None
    TASK_QUEUE_ENABLED: bool = False
    
    # Health Check Configuration
    HEALTH_CHECK_INTERVAL: int = 30
    HEALTH_CHECK_TIMEOUT: int = 5
    
    # API Documentation
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"
    OPENAPI_URL: str = "/openapi.json"
    
    # Environment-specific settings
    ENVIRONMENT: str = "development"
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        allowed = ["development", "staging", "production", "testing"]
        if v not in allowed:
            raise ValueError(f"Environment must be one of {allowed}")
        return v
    
    # Feature Flags
    FEATURE_FLAGS: Dict[str, bool] = {
        "new_ui": False,
        "advanced_analytics": False,
        "beta_features": False,
    }
    
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.ENVIRONMENT == "production"
    
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.ENVIRONMENT == "development"
    
    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.ENVIRONMENT == "testing"
    
    def get_database_url(self) -> str:
        """Get the complete database URL."""
        if self.DATABASE_URL:
            return self.DATABASE_URL
        raise ValueError("DATABASE_URL is not configured")
    
    def get_ai_config(self, provider: str) -> Dict[str, Any]:
        """Get AI provider configuration."""
        if provider.lower() == "openai":
            return {
                "api_key": self.OPENAI_API_KEY,
                "organization": self.OPENAI_ORG_ID,
                "model": self.OPENAI_MODEL_DEFAULT,
                "max_tokens": self.OPENAI_MAX_TOKENS,
                "temperature": self.OPENAI_TEMPERATURE,
            }
        elif provider.lower() == "anthropic":
            return {
                "api_key": self.ANTHROPIC_API_KEY,
                "model": self.ANTHROPIC_MODEL_DEFAULT,
                "max_tokens": self.ANTHROPIC_MAX_TOKENS,
            }
        elif provider.lower() == "gemini":
            return {
                "api_key": self.GEMINI_API_KEY,
                "model": self.GEMINI_MODEL_DEFAULT,
                "max_tokens": self.GEMINI_MAX_TOKENS,
                "temperature": self.GEMINI_TEMPERATURE,
            }
        return {}

    model_config = {
        "env_file": ".env",
        "case_sensitive": True,
        "extra": "ignore"
    }


settings = Settings()
