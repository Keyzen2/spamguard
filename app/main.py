from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
import logging
from datetime import datetime

from app.config import get_settings
from app.api.routes import router
from app.ml_model import spam_detector

# Configuración
settings = get_settings()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Eventos de inicio y cierre de la aplicación
    """
    # STARTUP
    logger.info("🚀 Iniciando SpamGuard AI API...")
    logger.info(f"📊 Environment: {settings.environment}")
    
    # Cargar modelo ML
    try:
        spam_detector.load_model('models/spam_model.pkl')
        logger.info(f"✅ Modelo ML cargado - Entrenado: {spam_detector.is_trained}")
    except Exception as e:
        logger.warning(f"⚠️  Modelo no disponible: {e}")
        logger.info("📝 API funcionará con reglas básicas (honeypot/time check)")
    
    yield
    
    # SHUTDOWN
    logger.info("👋 Cerrando SpamGuard AI API...")


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
    
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        
        # Log con formato mejorado
        log_message = (
            f"{request.method} {request.url.path} - "
            f"{response.status_code} - {process_time:.3f}s"
        )
        
        if response.status_code >= 400:
            logger.warning(f"⚠️  {log_message}")
        else:
            logger.info(f"📝 {log_message}")
        
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        logger.error(f"❌ Error processing request: {str(e)}")
        raise


# Manejador de errores de validación
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    logger.warning(f"❌ Validation error on {request.url.path}: {exc.errors()}")
    
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Error de validación",
            "errors": exc.errors()
        }
    )


# Manejador de errores generales
@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    logger.error(f"❌ Unhandled error on {request.url.path}: {str(exc)}")
    
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "message": str(exc) if settings.environment == "development" else "An error occurred"
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
        "model_loaded": spam_detector.is_trained,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "endpoints": {
            "docs": "/docs",
            "health": "/api/v1/health",
            "analyze": "/api/v1/analyze",
            "feedback": "/api/v1/feedback"
        }
    }


# Health check detallado (adicional al de routes.py)
@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "model": {
            "loaded": spam_detector.is_trained,
            "type": "ML" if spam_detector.is_trained else "Rules-based"
        },
        "database": "connected",  # Podrías verificar Supabase aquí
        "timestamp": datetime.utcnow().isoformat()
    }


# Para desarrollo local
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
