"""Configuración de la aplicación.

Este módulo define el modelo de configuración para la aplicación,
cargando valores desde variables de entorno o valores por defecto.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from dotenv import load_dotenv
import os

load_dotenv()

class Settings(BaseSettings):
    """
    Modelo de configuración de la aplicación.

    Atributos:
        PROJECT_NAME: Nombre del proyecto.
        PROJECT_VERSION: Versión actual del proyecto.
    """
    PROJECT_NAME: str = "Parqués Backend Distribuido"
    PROJECT_VERSION: str = "0.1.0"
    ENVIRONMENT : str = os.getenv("ENVIRONMENT")
    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings()