from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Supabase - Railway las inyectará automáticamente
    supabase_url: str
    supabase_key: str
    supabase_service_key: str
    
    # API
    api_version: str = "v1"
    environment: str = "production"
    debug: bool = False
    
    # ML
    model_path: str = "models/"
    retrain_threshold: int = 100
    min_samples_for_retrain: int = 50
    
    # Redis (opcional por ahora, lo configuraremos después)
    redis_url: Optional[str] = None
    
    class Config:
        env_file = ".env"  # Solo para desarrollo local
        env_file_encoding = 'utf-8'
        case_sensitive = False
        # Railway inyecta las variables directamente, no necesita .env

@lru_cache()
def get_settings():
    return Settings()
