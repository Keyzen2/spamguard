import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score
import joblib
from typing import Dict, List, Tuple
import os
from datetime import datetime
from app.database import Database
from app.config import get_settings

settings = get_settings()

class SpamDetector:
    """Modelo de ML para detectección de spam"""
    
    def __init__(self):
        self.model = None
        self.scaler = None
        self.feature_names = None
        self.is_trained = False
        
        # Intentar cargar modelo global pre-entrenado
        self._load_global_model()
    
    def _load_global_model(self):
        """Carga el modelo global pre-entrenado"""
        global_model_path = os.path.join(settings.model_path, 'global_model.joblib')
        global_scaler_path = os.path.join(settings.model_path, 'global_scaler.joblib')
        
        if os.path.exists(global_model_path) and os.path.exists(global_scaler_path):
            try:
                self.model = joblib.load(global_model_path)
                self.scaler = joblib.load(global_scaler_path)
                self.is_trained = True
                print("✅ Modelo global cargado exitosamente")
            except Exception as e:
                print(f"⚠️ Error cargando modelo global: {e}")
                self._create_baseline_model()
        else:
            print("ℹ️ No existe modelo global, creando modelo baseline...")
            self._create_baseline_model()
    
    def _create_baseline_model(self):
        """Crea un modelo baseline simple basado en reglas"""
        # Este modelo será usado hasta que tengamos datos para entrenar
        self.model = RandomForestClassifier(
            n_estimators=100,
            max_depth=10,
            random_state=42,
            class_weight='balanced'  # Importante para clases desbalanceadas
        )
        self.scaler = StandardScaler()
        self.is_trained = False
        print("✅ Modelo baseline creado")
    
    def predict(self, features: Dict) -> Dict:
        """
        Predice si un comentario es spam
        Retorna: {is_spam: bool, confidence: float, score: float, reasons: list}
        """
        
        # Si no hay modelo entrenado, usar reglas heurísticas
        if not self.is_trained:
            return self._rule_based_prediction(features)
        
        # Preparar features para el modelo
        feature_vector = self._prepare_features(features)
        
        # Escalar
        feature_scaled = self.scaler.transform([feature_vector])
        
        # Predicción
        prediction = self.model.predict(feature_scaled)[0]
        probabilities = self.model.predict_proba(feature_scaled)[0]
        
        # La probabilidad de spam (clase 1)
        spam_probability = probabilities[1] if len(probabilities) > 1 else probabilities[0]
        
        # Razones de la predicción
        reasons = self._get_prediction_reasons(features, spam_probability)
        
        return {
            'is_spam': bool(prediction == 1),
            'confidence': float(spam_probability),
            'score': float(spam_probability * 100),
            'reasons': reasons
        }
    
    def _rule_based_prediction(self, features: Dict) -> Dict:
        """
        Sistema de reglas para cuando no hay modelo entrenado
        """
        score = 0
        reasons = []
        
        # URLs sospechosas
        if features.get('url_count', 0) > 3:
            score += 30
            reasons.append(f"Contiene {features['url_count']} enlaces")
        
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
            'reasons': reasons[:5]  # Top 5 razones
        }
    
    def _prepare_features(self, features: Dict) -> List[float]:
        """Convierte el dict de features a un vector para el modelo"""
        
        # Definir el orden de las features
        if self.feature_names is None:
            self.feature_names = [
                'text_length', 'word_count', 'avg_word_length',
                'url_count', 'has_url', 'url_to_text_ratio',
                'unique_domains', 'has_suspicious_tld',
                'spam_keyword_count', 'spam_keyword_density',
                'special_char_ratio', 'uppercase_ratio', 'digit_ratio',
                'exclamation_count', 'question_count', 'has_html',
                'max_word_repetition', 'author_length', 'author_has_numbers',
                'author_all_caps', 'author_is_short',
                'email_domain_suspicious', 'email_has_numbers', 'email_length',
                'has_author_url', 'author_url_suspicious',
                'hour_of_day', 'is_night_time', 'is_weekend',
                'has_user_agent', 'is_bot'
            ]
        
        # Extraer valores en el orden correcto
        vector = []
        for feature_name in self.feature_names:
            value = features.get(feature_name, 0)
            # Convertir a float
            if isinstance(value, bool):
                value = 1.0 if value else 0.0
            vector.append(float(value))
        
        return vector
    
    def _get_prediction_reasons(self, features: Dict, spam_prob: float) -> List[str]:
        """Genera explicaciones de por qué se clasificó como spam o no"""
        reasons = []
        
        if spam_prob > 0.7:
            # Alta probabilidad de spam
            if features.get('spam_keyword_count', 0) > 0:
                reasons.append(f"Contiene palabras spam ({features['spam_keyword_count']})")
            if features.get('url_count', 0) > 2:
                reasons.append(f"Múltiples enlaces ({features['url_count']})")
            if features.get('has_suspicious_tld', 0) == 1:
                reasons.append("Dominios sospechosos")
            if features.get('is_bot', 0) == 1:
                reasons.append("Detectado como bot")
        else:
            # Baja probabilidad de spam
            reasons.append("Contenido parece legítimo")
            if features.get('text_length', 0) > 50:
                reasons.append("Comentario con contenido sustancial")
            if features.get('url_count', 0) == 0:
                reasons.append("Sin enlaces sospechosos")
        
        return reasons[:3]  # Top 3 razones
    
    async def train_site_model(self, site_id: str) -> Dict:
        """
        Entrena un modelo específico para un sitio
        """
        # Obtener datos de entrenamiento
        training_data = await Database.get_training_data(site_id, limit=1000)
        
        if len(training_data) < settings.min_samples_for_retrain:
            return {
                'success': False,
                'message': f'Se necesitan al menos {settings.min_samples_for_retrain} muestras etiquetadas'
            }
        
        # Preparar datos
        X = []
        y = []
        
        for item in training_data:
            features = item['features']
            label = 1 if item['actual_label'] == 'spam' else 0
            
            feature_vector = self._prepare_features(features)
            X.append(feature_vector)
            y.append(label)
        
        X = np.array(X)
        y = np.array(y)
        
        # Split train/test
        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, stratify=y
        )
        
        # Escalar
        self.scaler = StandardScaler()
        X_train_scaled = self.scaler.fit_transform(X_train)
        X_test_scaled = self.scaler.transform(X_test)
        
        # Entrenar modelo
        self.model = RandomForestClassifier(
            n_estimators=200,
            max_depth=15,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced',
            n_jobs=-1
        )
        
        self.model.fit(X_train_scaled, y_train)
        
        # Evaluar
        y_pred = self.model.predict(X_test_scaled)
        
        metrics = {
            'accuracy': accuracy_score(y_test, y_pred),
            'precision': precision_score(y_test, y_pred, zero_division=0),
            'recall': recall_score(y_test, y_pred, zero_division=0),
            'f1': f1_score(y_test, y_pred, zero_division=0)
        }
        
        # Guardar modelo
        model_path = os.path.join(settings.model_path, f'model_{site_id}.joblib')
        scaler_path = os.path.join(settings.model_path, f'scaler_{site_id}.joblib')
        
        os.makedirs(settings.model_path, exist_ok=True)
        joblib.dump(self.model, model_path)
        joblib.dump(self.scaler, scaler_path)
        
        self.is_trained = True
        
        return {
            'success': True,
            'metrics': metrics,
            'samples_used': len(training_data),
            'message': 'Modelo entrenado exitosamente'
        }

# Instancia global del detector
spam_detector = SpamDetector()
