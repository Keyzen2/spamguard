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
        global_model_path = os.path.join(settings.ml_model_path, 'global_model.joblib')  # ← CAMBIO AQUÍ
        global_scaler_path = os.path.join(settings.ml_model_path, 'global_scaler.joblib')  # ← CAMBIO AQUÍ
        
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
            class_weight='balanced'
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
