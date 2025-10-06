from fastapi import Header, HTTPException, Request
from typing import Optional
from app.database import Database
from app.utils import rate_limiter

def verify_api_key(x_api_key: str = Header(...)) -> str:  # ← SIN async
    """Valida la API key y retorna el site_id"""
    if not x_api_key or not x_api_key.startswith('sg_'):
        raise HTTPException(
            status_code=401,
            detail="API key inválida o faltante"
        )
    
    site_id = Database.validate_api_key(x_api_key)  # ← SIN await
    
    if not site_id:
        raise HTTPException(
            status_code=403,
            detail="API key no autorizada"
        )
    
    return site_id

def check_rate_limit(request: Request, x_api_key: str = Header(...)):  # ← SIN async
    """Verifica rate limiting por API key"""
    client_ip = request.client.host if request.client else "unknown"
    identifier = f"{x_api_key}:{client_ip}"
    
    if not rate_limiter.is_allowed(identifier, max_requests=1000, window_seconds=3600):
        remaining = rate_limiter.get_remaining(identifier, max_requests=1000)
        raise HTTPException(
            status_code=429,
            detail=f"Rate limit excedido. Requests restantes: {remaining}",
            headers={"Retry-After": "3600"}
        )
    
    return True
