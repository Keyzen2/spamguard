from fastapi import APIRouter, Depends, HTTPException, Request
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.api.dependencies import verify_api_key, check_rate_limit
from app.database import Database
from app.features import extract_features
from app.ml_model import spam_detector
from app.utils import sanitize_input, calculate_spam_score_explanation

router = APIRouter(prefix="/api/v1", tags=["spam-detection"])

# === MODELOS PYDANTIC ===

class CommentInput(BaseModel):
    content: str = Field(..., min_length=1, max_length=10000)
    author: str = Field(..., min_length=1, max_length=255)
    author_email: Optional[EmailStr] = None
    author_url: Optional[str] = Field(None, max_length=500)
    author_ip: str
    post_id: int
    user_agent: Optional[str] = None
    referer: Optional[str] = None
    
    class Config:
        json_schema_extra = {
            "example": {
                "content": "Great article! Thanks for sharing this information.",
                "author": "John Doe",
                "author_email": "john@example.com",
                "author_url": "https://johndoe.com",
                "author_ip": "192.168.1.1",
                "post_id": 123,
                "user_agent": "Mozilla/5.0...",
                "referer": "https://google.com"
            }
        }

class PredictionResponse(BaseModel):
    is_spam: bool
    confidence: float = Field(..., ge=0, le=1)
    spam_score: float = Field(..., ge=0, le=100)
    reasons: List[str]
    comment_id: str
    explanation: dict
    
class FeedbackInput(BaseModel):
    comment_id: str
    is_spam: bool
    
class StatsResponse(BaseModel):
    total_analyzed: int
    total_spam_blocked: int
    total_ham_approved: int
    accuracy: Optional[float]
    spam_block_rate: float
    last_retrain: Optional[str]

class ApiKeyResponse(BaseModel):
    site_id: str
    api_key: str
    created_at: str
    message: str

# === ENDPOINTS ===

@router.post("/analyze", response_model=PredictionResponse)
async def analyze_comment(
    comment: CommentInput,
    request: Request,
    site_id: str = Depends(verify_api_key),
    _: bool = Depends(check_rate_limit)
):
    """
    **Analiza un comentario y predice si es spam**
    
    Este endpoint procesa el comentario, extrae características,
    ejecuta el modelo de ML y retorna la predicción con explicación.
    
    - **content**: Texto del comentario (requerido)
    - **author**: Nombre del autor (requerido)
    - **author_email**: Email del autor (opcional pero recomendado)
    - **author_ip**: IP del autor (requerido)
    - **post_id**: ID del post donde se comenta (requerido)
    """
    try:
        # Sanitizar inputs
        comment_data = {
            'content': sanitize_input(comment.content),
            'author': sanitize_input(comment.author),
            'author_email': comment.author_email,
            'author_url': comment.author_url,
            'author_ip': comment.author_ip,
            'post_id': comment.post_id,
            'user_agent': comment.user_agent,
            'referer': comment.referer
        }
        
        # 1. Extraer características
        features = extract_features(comment_data)
        
        # 2. Predicción con modelo ML
        prediction = spam_detector.predict(features)
        
        # 3. Generar explicación detallada
        explanation = calculate_spam_score_explanation(
            features,
            prediction['is_spam'],
            prediction['confidence']
        )
        
        # 4. Guardar análisis en base de datos
        comment_id = await Database.save_comment_analysis(
            site_id=site_id,
            comment_data=comment_data,
            features=features,
            prediction=prediction
        )
        
        return PredictionResponse(
            is_spam=prediction['is_spam'],
            confidence=prediction['confidence'],
            spam_score=prediction['score'],
            reasons=prediction['reasons'],
            comment_id=comment_id,
            explanation=explanation
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error procesando comentario: {str(e)}"
        )

@router.post("/feedback")
async def submit_feedback(
    feedback: FeedbackInput,
    site_id: str = Depends(verify_api_key),
    _: bool = Depends(check_rate_limit)
):
    """
    **Envía feedback sobre la clasificación de un comentario**
    
    Permite corregir predicciones incorrectas. Este feedback
    se usa para reentrenar y mejorar el modelo.
    
    - **comment_id**: ID del comentario analizado
    - **is_spam**: Clasificación correcta (true si es spam, false si es legítimo)
    """
    try:
        # Obtener el comentario original
        result = await Database.supabase.table('comments_analyzed')\
            .select('predicted_label')\
            .eq('id', feedback.comment_id)\
            .eq('site_id', site_id)\
            .execute()
        
        if not result.data:
            raise HTTPException(
                status_code=404,
                detail="Comentario no encontrado"
            )
        
        old_label = result.data[0]['predicted_label']
        new_label = 'spam' if feedback.is_spam else 'ham'
        
        # Guardar feedback
        await Database.save_feedback(
            comment_id=feedback.comment_id,
            site_id=site_id,
            correct_label=new_label,
            old_label=old_label
        )
        
        # Verificar si es momento de reentrenar
        should_retrain = await Database.check_retrain_needed(site_id)
        
        response = {
            "status": "success",
            "message": "Feedback recibido correctamente",
            "queued_for_training": should_retrain
        }
        
        # Si hay suficiente feedback, reentrenar en background
        if should_retrain:
            # TODO: Implementar task en background con Celery o similar
            response["message"] += ". El modelo será reentrenado próximamente."
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error guardando feedback: {str(e)}"
        )

@router.get("/stats", response_model=StatsResponse)
async def get_statistics(
    site_id: str = Depends(verify_api_key)
):
    """
    **Obtiene estadísticas del sitio**
    
    Retorna métricas sobre comentarios analizados,
    spam bloqueado, accuracy del modelo, etc.
    """
    try:
        stats = await Database.get_site_statistics(site_id)
        
        if not stats:
            # Sitio nuevo sin estadísticas
            return StatsResponse(
                total_analyzed=0,
                total_spam_blocked=0,
                total_ham_approved=0,
                accuracy=None,
                spam_block_rate=0.0,
                last_retrain=None
            )
        
        return StatsResponse(**stats)
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error obteniendo estadísticas: {str(e)}"
        )

@router.post("/retrain")
async def trigger_retrain(
    site_id: str = Depends(verify_api_key)
):
    """
    **Fuerza el reentrenamiento del modelo**
    
    Útil cuando quieres actualizar el modelo inmediatamente
    sin esperar al threshold automático.
    """
    try:
        result = await spam_detector.train_site_model(site_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=result['message']
            )
        
        # Actualizar timestamp de último reentrenamiento
        await Database.supabase.table('site_stats')\
            .update({'last_retrain': datetime.utcnow().isoformat()})\
            .eq('site_id', site_id)\
            .execute()
        
        return {
            "status": "success",
            "message": result['message'],
            "metrics": result['metrics'],
            "samples_used": result['samples_used']
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error reentrenando modelo: {str(e)}"
        )

@router.get("/health")
async def health_check():
    """
    **Health check del servicio**
    
    Verifica que la API esté funcionando correctamente.
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "model_status": "trained" if spam_detector.is_trained else "baseline",
        "version": "1.0.0"
    }

# Endpoint especial para crear nuevas API keys (protegido)
@router.post("/register-site", response_model=ApiKeyResponse)
async def register_new_site(
    site_url: str,
    admin_email: EmailStr,
    # TODO: Agregar autenticación adicional aquí
):
    """
    **Registra un nuevo sitio y genera API key**
    
    Este endpoint debería estar protegido con autenticación adicional
    en producción (ej: JWT, OAuth, etc.)
    """
    try:
        # Generar site_id único basado en URL
        import hashlib
        site_id = hashlib.sha256(site_url.encode()).hexdigest()[:16]
        
        # Verificar si ya existe
        existing = await Database.supabase.table('site_stats')\
            .select('site_id')\
            .eq('site_id', site_id)\
            .execute()
        
        if existing.data:
            raise HTTPException(
                status_code=400,
                detail="Este sitio ya está registrado"
            )
        
        # Crear nuevo registro
        api_key = Database.generate_api_key()
        
        new_site = {
            'site_id': site_id,
            'api_key': api_key,
            'total_analyzed': 0,
            'total_spam_blocked': 0,
            'total_ham_approved': 0,
            'created_at': datetime.utcnow().isoformat()
        }
        
        await Database.supabase.table('site_stats').insert(new_site).execute()
        
        return ApiKeyResponse(
            site_id=site_id,
            api_key=api_key,
            created_at=new_site['created_at'],
            message="Sitio registrado exitosamente. Guarda tu API key de forma segura."
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Error registrando sitio: {str(e)}"
        )
