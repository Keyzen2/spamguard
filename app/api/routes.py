from fastapi import APIRouter, Depends, HTTPException, Request, Header
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from datetime import datetime

from app.api.dependencies import verify_api_key, check_rate_limit
from app.database import Database, supabase  # ← IMPORTANTE: importar supabase
from app.features import extract_features
from app.utils import sanitize_input, calculate_spam_score_explanation
from app.ml_model import spam_detector


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
        comment_id = Database.save_comment_analysis(
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
    """
    try:
        # Obtener el comentario original - CORREGIDO
        result = supabase.table('comments_analyzed')\
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
        Database.save_feedback(
            comment_id=feedback.comment_id,
            site_id=site_id,
            correct_label=new_label,
            old_label=old_label
        )
        
        # Verificar si es momento de reentrenar
        should_retrain = Database.check_retrain_needed(site_id)
        
        response = {
            "status": "success",
            "message": "Feedback recibido correctamente",
            "queued_for_training": should_retrain
        }
        
        if should_retrain:
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
    """
    try:
        stats = Database.get_site_statistics(site_id)
        
        if not stats:
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
    """
    try:
        result = spam_detector.train_site_model(site_id)
        
        if not result['success']:
            raise HTTPException(
                status_code=400,
                detail=result['message']
            )
        
        # Actualizar timestamp - CORREGIDO
        supabase.table('site_stats')\
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
    """
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "model_status": "trained" if spam_detector.is_trained else "baseline",
        "version": "1.0.0"
    }

@router.post("/register-site", response_model=ApiKeyResponse)
async def register_new_site(
    site_url: str,
    admin_email: EmailStr,
):
    """
    **Registra un nuevo sitio y genera API key**
    """
    try:
        # Generar site_id único basado en URL
        import hashlib
        site_id = hashlib.sha256(site_url.encode()).hexdigest()[:16]
        
        # Verificar si ya existe - CORREGIDO
        existing = supabase.table('site_stats')\
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
        
        # CORREGIDO
        supabase.table('site_stats').insert(new_site).execute()
        
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
        
@router.post("/admin/init-training-data")
async def init_training_data(
    x_admin_secret: str = Header(..., alias="X-Admin-Secret")
):
    """
    Endpoint temporal para inicializar datos de entrenamiento
    IMPORTANTE: Proteger muy bien - Solo uso administrativo
    """
    settings = get_settings()
    
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        # Importar la función del script
        import sys
        import os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../..'))
        
        from scripts.init_training_data import insert_training_data
        
        result = insert_training_data()
        return {
            "status": "success",
            "message": "Training data initialized",
            "data": result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/admin/train-model")
async def train_global_model_endpoint(
    x_admin_secret: str = Header(..., alias="X-Admin-Secret")
):
    """
    Endpoint temporal para entrenar modelo global
    IMPORTANTE: Proteger muy bien - Solo uso administrativo
    """
    # AGREGAR ESTOS IMPORTS AQUÍ DENTRO
    from app.config import get_settings
    from app.ml_model import spam_detector
    import shutil
    import os
    
    settings = get_settings()
    
    if x_admin_secret != settings.admin_secret:
        raise HTTPException(status_code=403, detail="Forbidden")
    
    try:
        result = spam_detector.train_site_model('global')
        
        if result['success']:
            
            old_model = os.path.join(settings.ml_model_path, 'model_global.joblib')
            old_scaler = os.path.join(settings.ml_model_path, 'scaler_global.joblib')
            new_model = os.path.join(settings.ml_model_path, 'global_model.joblib')
            new_scaler = os.path.join(settings.ml_model_path, 'global_scaler.joblib')
            
            os.makedirs(settings.ml_model_path, exist_ok=True)
            
            if os.path.exists(old_model):
                shutil.copy(old_model, new_model)
                shutil.copy(old_scaler, new_scaler)
        
        return {
            "status": "success" if result['success'] else "error",
            "metrics": result.get('metrics'),
            "samples_used": result.get('samples_used'),
            "message": result.get('message')
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
