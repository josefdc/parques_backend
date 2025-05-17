"""Application configuration settings.

This module defines the configuration model for the application,
loading settings from environment variables or default values.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    """Application settings model.

    Attributes:
        PROJECT_NAME: The name of the project.
        PROJECT_VERSION: The current version of the project.
        model_config: Pydantic model configuration, e.g., for .env file loading.
    """
    PROJECT_NAME: str = "Parqués Backend Distribuido"
    PROJECT_VERSION: str = "0.1.0"
    # For Pydantic v2, to load from a .env file, configure model_config within the class:
    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()