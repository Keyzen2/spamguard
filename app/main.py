from fastapi import FastAPI, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
import uvicorn
from datetime import datetime
import numpy as np

app = FastAPI(
    title="SpamGuard AI API",
    description="API de detección de spam con ML",
    version="1.0.0"
)

# CORS para WordPress
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # En producción, especificar dominios
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class CommentInput(BaseModel):
    content: str
    author: str
    author_email: Optional[EmailStr] = None
    author_url: Optional[str] = None
    author_ip: str
    post_id: int
    user_agent: Optional[str] = None
    referer: Optional[str] = None

class PredictionResponse(BaseModel):
    is_spam: bool
    confidence: float
    spam_score: float
    reasons: List[str]
    comment_id: str

class FeedbackInput(BaseModel):
    comment_id: str
    is_spam: bool  # La clasificación correcta

# Dependency para validar API key
async def verify_api_key(x_api_key: str = Header(...)):
    # Validar contra Supabase
    if not await is_valid_api_key(x_api_key):
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return x_api_key

@app.get("/")
async def root():
    return {"message": "SpamGuard AI API", "status": "online"}

@app.post("/api/v1/analyze", response_model=PredictionResponse)
async def analyze_comment(
    comment: CommentInput,
    api_key: str = Depends(verify_api_key)
):
    """
    Analiza un comentario y predice si es spam
    """
    try:
        # 1. Extraer características
        features = await extract_features(comment)
        
        # 2. Obtener sitio del API key
        site_id = await get_site_id_from_api_key(api_key)
        
        # 3. Predicción con modelo
        prediction = await predict_spam(features, site_id)
        
        # 4. Guardar en base de datos
        comment_id = await save_analysis(comment, features, prediction, site_id)
        
        # 5. Retornar resultado
        return PredictionResponse(
            is_spam=prediction['is_spam'],
            confidence=prediction['confidence'],
            spam_score=prediction['score'],
            reasons=prediction['reasons'],
            comment_id=comment_id
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/feedback")
async def submit_feedback(
    feedback: FeedbackInput,
    api_key: str = Depends(verify_api_key)
):
    """
    Recibe feedback del usuario para mejorar el modelo
    """
    site_id = await get_site_id_from_api_key(api_key)
    await queue_feedback(feedback, site_id)
    
    # Verificar si es momento de reentrenar
    await check_retrain_trigger(site_id)
    
    return {"status": "feedback_received", "queued_for_training": True}

@app.get("/api/v1/stats")
async def get_stats(api_key: str = Depends(verify_api_key)):
    """
    Obtiene estadísticas del sitio
    """
    site_id = await get_site_id_from_api_key(api_key)
    stats = await get_site_statistics(site_id)
    return stats

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
