"""
Application configuration management.
Loads environment variables and provides configuration to the app.
"""

from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Azure OpenAI Configuration
    azure_openai_api_key: str
    azure_openai_endpoint: str
    azure_openai_deployment_name: str = "gpt-4"
    azure_openai_api_version: str = "2024-08-01-preview"
    
    # Database Configuration
    database_url: str
    
    # Application Settings
    environment: str = "development"
    debug: bool = True
    secret_key: str = "dev-secret-key"
    
    # Frontend URL (for CORS)
    frontend_url: str = "http://localhost:5173"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


# Global settings instance
settings = Settings()


