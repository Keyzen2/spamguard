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
    
    # ML - Renombrado para evitar conflicto con 'model_'
    ml_model_path: str = "models/"  # ← CAMBIO AQUÍ
    retrain_threshold: int = 100
    min_samples_for_retrain: int = 50

    # Admin secret para endpoints sensibles
    admin_secret: str = "tu_clave_super_secreta_aqui_123456"
    
    # Redis (opcional por ahora, lo configuraremos después)
    redis_url: Optional[str] = None
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": 'utf-8',
        "case_sensitive": False,
        "protected_namespaces": ('settings_',)  # ← Y ESTO
    }

@lru_cache()
def get_settings():
    return Settings()
