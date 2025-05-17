# app/core/config.py
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    PROJECT_NAME: str = "Parqués Backend Distribuido"
    PROJECT_VERSION: str = "0.1.0"
    # Si usas Pydantic v2 y quieres cargar .env, la config va dentro de la clase:
    # model_config = SettingsConfigDict(env_file=".env", env_file_encoding='utf-8', extra='ignore')

settings = Settings() # <--- ASEGÚRATE DE QUE ESTA LÍNEA EXISTA Y SEA CORRECTA