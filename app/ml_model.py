import numpy as np
import joblib
from typing import Dict, List
import os
from pathlib import Path

from app.config import get_settings

settings = get_settings()

class SpamDetector:
    """Modelo de ML para detección de spam"""
    
    def __init__(self):
        self.model = None
        self.is_trained = False
        
        # Intentar cargar modelo pre-entrenado
        self._load_global_model()
    
    def _load_global_model(self):
        """Carga el modelo global pre-entrenado"""
        model_path = Path('models') / 'spam_model.pkl'
        
        if model_path.exists():
            try:
                self.model = joblib.load(model_path)
                self.is_trained = True
                print("✅ Modelo global cargado exitosamente")
            except Exception as e:
                print(f"⚠️ Error cargando modelo: {e}")
                self.is_trained = False
        else:
            print("ℹ️ No existe modelo entrenado, usando reglas básicas")
            self.is_trained = False
    
    def load_model(self, model_path: str):
        """
        Carga un modelo desde un archivo .pkl
        
        Args:
            model_path: Ruta al archivo del modelo
        """
        try:
            self.model = joblib.load(model_path)
            self.is_trained = True
            print(f"✅ Modelo cargado desde: {model_path}")
        except Exception as e:
            print(f"❌ Error cargando modelo desde {model_path}: {e}")
            self.is_trained = False
    
    def predict(self, features: Dict) -> Dict:
        """
        Predice si un comentario es spam
        
        Args:
            features: Diccionario con características extraídas
            
        Returns:
            Dict con: is_spam, confidence, score, reasons
        """
        
        # Si no hay modelo entrenado, usar reglas heurísticas
        if not self.is_trained or self.model is None:
            return self._rule_based_prediction(features)
        
        try:
            # El modelo es un pipeline de scikit-learn (TfidfVectorizer + MultinomialNB)
            # Necesita el texto del comentario directamente
            content = features.get('content', '')
            
            if not content:
                # Fallback a reglas si no hay contenido
                return self._rule_based_prediction(features)
            
            # Predicción del modelo
            prediction = self.model.predict([content])[0]
            probabilities = self.model.predict_proba([content])[0]
            
            # Probabilidad de spam (clase 1)
            spam_probability = probabilities[1]
            
            # Determinar si es spam (umbral 0.5)
            is_spam = prediction == 1
            
            # Generar razones
            reasons = self._get_ml_prediction_reasons(
                features, 
                spam_probability, 
                is_spam
            )
            
            return {
                'is_spam': bool(is_spam),
                'confidence': float(spam_probability),
                'score': float(spam_probability * 100),
                'reasons': reasons
            }
            
        except Exception as e:
            print(f"⚠️ Error en predicción ML: {e}")
            # Fallback a reglas
            return self._rule_based_prediction(features)
    
    def _rule_based_prediction(self, features: Dict) -> Dict:
        """
        Sistema de reglas para cuando no hay modelo entrenado
        """
        score = 0
        reasons = []
        
        # URLs sospechosas
        url_count = features.get('url_count', 0)
        if url_count > 3:
            score += 30
            reasons.append(f"Contiene {url_count} enlaces")
        
        if features.get('has_suspicious_tld', 0) == 1:
            score += 25
            reasons.append("Dominios sospechosos detectados")
        
        # Palabras spam
        spam_keywords = features.get('spam_keyword_count', 0)
        if spam_keywords > 0:
            score += spam_keywords * 15
            reasons.append(f"Contiene {spam_keywords} palabras spam")
        
        # Email sospechoso
        if features.get('email_domain_suspicious', 0) == 1:
            score += 20
            reasons.append("Email de dominio temporal")
        
        # Mayúsculas excesivas
        if features.get('uppercase_ratio', 0) > 0.5:
            score += 15
            reasons.append("Exceso de mayúsculas")
        
        # Caracteres especiales
        if features.get('special_char_ratio', 0) > 0.3:
            score += 10
            reasons.append("Muchos caracteres especiales")
        
        # HTML en comentario
        if features.get('has_html', 0) == 1:
            score += 20
            reasons.append("Contiene código HTML")
        
        # Comportamiento bot
        if features.get('is_bot', 0) == 1:
            score += 35
            reasons.append("Detectado como bot")
        
        # Sin user agent
        if features.get('has_user_agent', 0) == 0:
            score += 15
            reasons.append("Sin user agent")
        
        # Normalizar score a 0-1
        confidence = min(score / 100, 1.0)
        is_spam = confidence > 0.5
        
        if not is_spam and not reasons:
            reasons.append("No se detectaron señales de spam")
        
        return {
            'is_spam': is_spam,
            'confidence': confidence,
            'score': score,
            'reasons': reasons[:5]
        }
    
    def _get_ml_prediction_reasons(
        self, 
        features: Dict, 
        spam_prob: float,
        is_spam: bool
    ) -> List[str]:
        """
        Genera explicaciones basadas en la predicción del modelo ML
        """
        reasons = []
        
        if is_spam:
            # Alta probabilidad de spam
            reasons.append(f"Modelo ML detectó spam ({spam_prob*100:.1f}% confianza)")
            
            if features.get('spam_keyword_count', 0) > 0:
                reasons.append(f"Contiene palabras spam ({features['spam_keyword_count']})")
            
            if features.get('url_count', 0) > 2:
                reasons.append(f"Múltiples enlaces ({features['url_count']})")
            
            if features.get('has_suspicious_tld', 0) == 1:
                reasons.append("Dominios sospechosos")
            
            if features.get('is_bot', 0) == 1:
                reasons.append("Detectado como bot")
        else:
            # Comentario legítimo
            reasons.append(f"Modelo ML: contenido legítimo ({(1-spam_prob)*100:.1f}% confianza)")
            
            if features.get('text_length', 0) > 50:
                reasons.append("Comentario con contenido sustancial")
            
            if features.get('url_count', 0) == 0:
                reasons.append("Sin enlaces sospechosos")
            
            if features.get('spam_keyword_count', 0) == 0:
                reasons.append("Sin palabras spam detectadas")
        
        return reasons[:5]


# Instancia global del detector
spam_detector = SpamDetector()
