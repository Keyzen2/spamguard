from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
from datetime import datetime

from app.config import get_settings
from app.api.routes import router
from app.ml_model import spam_detector

settings = get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de inicio y cierre de la aplicación
    """
    # Startup
    print("🚀 Iniciando SpamGuard AI API...")
    print(f"📊 Environment: {settings.environment}")
    print(f"🤖 Modelo: {'Entrenado' if spam_detector.is_trained else 'Baseline (reglas)'}")
    
    yield
    
    # Shutdown
    print("👋 Cerrando SpamGuard AI API...")

# Crear aplicación FastAPI
app = FastAPI(
    title="SpamGuard AI API",
    description="API inteligente de detección de spam con Machine Learning",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción: especificar dominios permitidos
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Middleware para logging de requests
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    
    response = await call_next(request)
    
    process_time = time.time() - start_time
    
    print(f"📝 {request.method} {request.url.path} - {response.status_code} - {process_time:.3f}s")
    
    response.headers["X-Process-Time"] = str(process_time)
    
    return response

# Manejador de errores de validación
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validación",
            "errors": exc.errors()
        }
    )

# Incluir rutas
app.include_router(router)

# Ruta raíz
@app.get("/")
async def root():
    return {
        "service": "SpamGuard AI API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.utcnow().isoformat(),
        "docs": "/docs",
        "health": "/api/v1/health"
    }

# Para desarrollo local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True  # Hot reload en desarrollo
    )
