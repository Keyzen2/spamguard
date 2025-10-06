import re
from typing import Dict, List
from urllib.parse import urlparse
import hashlib
from datetime import datetime

class FeatureExtractor:
    """
    Extrae características relevantes de un comentario para el modelo ML
    """
    
    # Lista de palabras comunes en spam
    SPAM_KEYWORDS = [
        'viagra', 'cialis', 'pharmacy', 'casino', 'poker',
        'loan', 'mortgage', 'credit', 'earn money', 'work from home',
        'click here', 'buy now', 'limited offer', 'act now',
        'free money', 'weight loss', 'bitcoin', 'crypto'
    ]
    
    # Dominios de email sospechosos
    SUSPICIOUS_DOMAINS = [
        'tempmail.com', 'guerrillamail.com', '10minutemail.com',
        'mailinator.com', 'throwaway.email'
    ]
    
    def __init__(self):
        self.suspicious_tlds = ['.ru', '.cn', '.tk', '.ml', '.ga']
    
    async def extract(self, comment: CommentInput) -> Dict:
        """
        Extrae todas las características del comentario
        """
        features = {}
        
        # === CARACTERÍSTICAS DE TEXTO ===
        content = comment.content.lower()
        
        # Básicas
        features['text_length'] = len(comment.content)
        features['word_count'] = len(comment.content.split())
        features['avg_word_length'] = (
            sum(len(word) for word in comment.content.split()) / 
            max(len(comment.content.split()), 1)
        )
        
        # URLs y enlaces
        urls = re.findall(r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', 
                         comment.content)
        features['url_count'] = len(urls)
        features['has_url'] = len(urls) > 0
        features['url_to_text_ratio'] = len(''.join(urls)) / max(len(comment.content), 1)
        
        # Análisis de URLs
        if urls:
            features['unique_domains'] = len(set(urlparse(url).netloc for url in urls))
            features['has_suspicious_tld'] = any(
                any(url.endswith(tld) for tld in self.suspicious_tlds) 
                for url in urls
            )
        else:
            features['unique_domains'] = 0
            features['has_suspicious_tld'] = False
        
        # Palabras spam
        spam_word_count = sum(1 for keyword in self.SPAM_KEYWORDS if keyword in content)
        features['spam_keyword_count'] = spam_word_count
        features['has_spam_keywords'] = spam_word_count > 0
        
        # Caracteres especiales y patrones
        features['special_char_ratio'] = len(re.findall(r'[^a-zA-Z0-9\s]', comment.content)) / max(len(comment.content), 1)
        features['uppercase_ratio'] = sum(1 for c in comment.content if c.isupper()) / max(len(comment.content), 1)
        features['digit_ratio'] = sum(1 for c in comment.content if c.isdigit()) / max(len(comment.content), 1)
        features['exclamation_count'] = comment.content.count('!')
        features['question_count'] = comment.content.count('?')
        
        # === CARACTERÍSTICAS DEL AUTOR ===
        
        # Email
        if comment.author_email:
            email_domain = comment.author_email.split('@')[1] if '@' in comment.author_email else ''
            features['email_domain_suspicious'] = email_domain in self.SUSPICIOUS_DOMAINS
            features['email_length'] = len(comment.author_email)
            
            # Hash del email para patrones (privacidad)
            features['email_hash'] = hashlib.md5(comment.author_email.encode()).hexdigest()[:8]
        else:
            features['has_email'] = False
            features['email_domain_suspicious'] = False
            features['email_length'] = 0
        
        # Nombre del autor
        features['author_length'] = len(comment.author)
        features['author_has_numbers'] = bool(re.search(r'\d', comment.author))
        features['author_all_caps'] = comment.author.isupper() if comment.author else False
        
        # URL del autor
        if comment.author_url:
            features['has_author_url'] = True
            author_domain = urlparse(comment.author_url).netloc
            features['author_url_suspicious_tld'] = any(
                author_domain.endswith(tld) for tld in self.suspicious_tlds
            )
        else:
            features['has_author_url'] = False
            features['author_url_suspicious_tld'] = False
        
        # === CARACTERÍSTICAS DE COMPORTAMIENTO ===
        
        # IP
        features['ip_hash'] = hashlib.md5(comment.author_ip.encode()).hexdigest()[:8]
        
        # Hora del día (spam suele venir en horarios específicos)
        hour = datetime.now().hour
        features['hour_of_day'] = hour
        features['is_night_time'] = hour < 6 or hour > 23
        
        # User agent
        if comment.user_agent:
            features['has_user_agent'] = True
            features['is_bot'] = bool(re.search(r'bot|crawler|spider', comment.user_agent.lower()))
        else:
            features['has_user_agent'] = False
            features['is_bot'] = False
        
        return features

# Función helper
async def extract_features(comment: CommentInput) -> Dict:
    extractor = FeatureExtractor()
    return await extractor.extract(comment)
