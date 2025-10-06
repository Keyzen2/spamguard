"""
Script para cargar dataset inicial de spam y entrenar modelo global
"""
import pandas as pd
import requests
from supabase import create_client
import os
from datetime import datetime
import uuid

# Configuración
SUPABASE_URL = os.getenv('SUPABASE_URL')
SUPABASE_SERVICE_KEY = os.getenv('SUPABASE_SERVICE_KEY')

supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

# Dataset público de spam de YouTube (muy bueno para comentarios)
DATASET_URL = "https://raw.githubusercontent.com/nealrs/yt-spam/master/Youtube-Spam-Dataset.csv"

def download_spam_dataset():
    """Descarga dataset público de spam"""
    print("📥 Descargando dataset de spam...")
    
    # Alternativas de datasets:
    # 1. YouTube Spam Dataset
    # 2. SMS Spam Collection
    # 3. Email Spam Dataset
    
    df = pd.read_csv(DATASET_URL)
    print(f"✅ Dataset descargado: {len(df)} comentarios")
    
    return df

def prepare_synthetic_comments():
    """Crea comentarios sintéticos de spam y ham para entrenamiento inicial"""
    
    spam_comments = [
        # Spam obvio
        "BUY VIAGRA NOW! CHEAP PRICES! Click here: http://spam.ru",
        "Make money fast! Work from home! Visit casino.tk for details!!!",
        "Congratulations! You won $1,000,000! Click here to claim prize",
        "Free Bitcoin! Cryptocurrency investment! lottery.ml Join now!!!",
        "CHEAP LOANS! BAD CREDIT OK! Apply now at loans-fast.cn",
        "Weight loss miracle! Lose 50 pounds in 1 week! pharmacy.ga",
        "Hot singles in your area! Click here dating.tk NOW!!!",
        "Prince needs help transferring inheritance. Email me for millions!",
        "CLICK HERE NOW! Limited time offer! BUY NOW ACT FAST!!!",
        "Earn $5000 per week working from home! No experience needed!",
        
        # Spam moderado
        "Check out my website for amazing deals http://mysite.com",
        "Great post! Visit my blog at http://blog1.com and http://blog2.com",
        "Nice article. Buy my ebook here: http://ebook.com",
        "Interesting. See more at http://link1.com http://link2.com http://link3.com",
        "Thanks for sharing! <a href='spam.com'>Click here</a>",
        
        # Spam sutil
        "Great post!!!!!!!!",
        "AWESOME ARTICLE!!!!! LOVE IT!!!!!",
        "niceeeee poooost greaaaat joooob",
        "first comment lol subscribe to my channel",
        "F1RST C0MM3NT!!!1!",
    ]
    
    ham_comments = [
        # Comentarios legítimos largos
        "This is a really insightful article. I particularly appreciated your analysis of the economic impacts. The data you presented clearly supports your conclusions. Thank you for sharing this valuable perspective.",
        "Great explanation! I've been struggling to understand this concept for weeks, and your clear breakdown finally made it click for me. The examples you used were perfect.",
        "I have a different perspective on this issue. While I agree with most of your points, I think we also need to consider the environmental impact. What are your thoughts on that aspect?",
        "Thank you for writing this. As someone who works in this field, I can confirm that your observations are spot-on. This is exactly what we're seeing in practice.",
        "Excellent tutorial! I followed your steps and it worked perfectly. One suggestion: it might be helpful to add a troubleshooting section for common errors.",
        
        # Comentarios legítimos cortos
        "Thanks for sharing this!",
        "Very helpful, appreciate it.",
        "Interesting perspective.",
        "Great work!",
        "This helped me a lot, thank you.",
        "Well explained.",
        "I learned something new today.",
        "Bookmarking this for later.",
        "Could you elaborate on the second point?",
        "What source did you use for this data?",
        
        # Comentarios con preguntas legítimas
        "How does this compare to the previous version?",
        "What would you recommend for beginners?",
        "Has anyone tried implementing this in production?",
        "Are there any prerequisites for this approach?",
        "What are the potential drawbacks of this method?",
    ]
    
    comments = []
    
    # Agregar spam
    for i, content in enumerate(spam_comments):
        comments.append({
            'content': content,
            'author': f'Spammer{i}',
            'author_email': f'spam{i}@tempmail.com' if i % 2 == 0 else None,
            'is_spam': True
        })
    
    # Agregar ham
    for i, content in enumerate(ham_comments):
        comments.append({
            'content': content,
            'author': f'User{i}',
            'author_email': f'user{i}@gmail.com' if i % 2 == 0 else None,
            'is_spam': False
        })
    
    return comments

def insert_training_data(comments, site_id='global'):
    """Inserta datos de entrenamiento en Supabase"""
    
    print(f"💾 Insertando {len(comments)} comentarios en la base de datos...")
    
    # Importar extractor de features
    import sys
    sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
    from app.features import extract_features
    
    inserted = 0
    
    for comment in comments:
        try:
            # Preparar datos del comentario
            comment_data = {
                'content': comment['content'],
                'author': comment.get('author', 'Anonymous'),
                'author_email': comment.get('author_email', None),
                'author_ip': '127.0.0.1',
                'post_id': 1,
                'author_url': None,
                'user_agent': 'Training Script',
                'referer': None
            }
            
            # Extraer features
            features = extract_features(comment_data)
            
            # Determinar label
            label = 'spam' if comment['is_spam'] else 'ham'
            
            # Insertar en base de datos
            data = {
                'id': str(uuid.uuid4()),
                'site_id': site_id,
                'comment_content': comment['content'],
                'comment_author': comment_data['author'],
                'comment_author_email': comment_data.get('author_email'),
                'comment_author_ip': '127.0.0.1',
                'comment_author_url': None,
                'post_id': 1,
                'features': features,
                'predicted_label': label,  # En este caso conocemos el label real
                'actual_label': label,  # Marcamos como ya verificado
                'prediction_confidence': 1.0,
                'user_agent': 'Training Script',
                'created_at': datetime.utcnow().isoformat()
            }
            
            supabase.table('comments_analyzed').insert(data).execute()
            inserted += 1
            
            if inserted % 10 == 0:
                print(f"  ✓ {inserted}/{len(comments)} insertados...")
                
        except Exception as e:
            print(f"  ✗ Error insertando comentario: {e}")
            continue
    
    print(f"✅ {inserted} comentarios insertados correctamente")
    
    return inserted

def update_site_stats(site_id='global', total_comments=0):
    """Actualiza o crea estadísticas del sitio global"""
    
    # Contar spam y ham
    spam_count = supabase.table('comments_analyzed')\
        .select('id', count='exact')\
        .eq('site_id', site_id)\
        .eq('actual_label', 'spam')\
        .execute()
    
    ham_count = supabase.table('comments_analyzed')\
        .select('id', count='exact')\
        .eq('site_id', site_id)\
        .eq('actual_label', 'ham')\
        .execute()
    
    stats_data = {
        'site_id': site_id,
        'total_analyzed': total_comments,
        'total_spam_blocked': spam_count.count if spam_count.count else 0,
        'total_ham_approved': ham_count.count if ham_count.count else 0,
        'accuracy': 1.0,  # Dataset de entrenamiento es 100% correcto
        'api_key': f'sg_global_training_{uuid.uuid4().hex[:16]}',
        'created_at': datetime.utcnow().isoformat()
    }
    
    # Intentar insertar o actualizar
    try:
        supabase.table('site_stats').upsert(stats_data).execute()
        print(f"✅ Estadísticas actualizadas para site_id: {site_id}")
    except Exception as e:
        print(f"⚠️ Error actualizando estadísticas: {e}")

def main():
    """Función principal"""
    print("🚀 Inicializando datos de entrenamiento...")
    print("=" * 60)
    
    # Opción 1: Comentarios sintéticos (más rápido)
    print("\n📝 Creando comentarios sintéticos...")
    comments = prepare_synthetic_comments()
    
    # Opción 2: Descargar dataset público (descomentar si quieres)
    # try:
    #     df = download_spam_dataset()
    #     # Procesar el dataset según su formato
    #     # ...
    # except Exception as e:
    #     print(f"⚠️ No se pudo descargar dataset público: {e}")
    #     print("Usando comentarios sintéticos...")
    #     comments = prepare_synthetic_comments()
    
    # Insertar datos
    total = insert_training_data(comments, site_id='global')
    
    # Actualizar estadísticas
    update_site_stats(site_id='global', total_comments=total)
    
    print("\n" + "=" * 60)
    print("✅ ¡Inicialización completada!")
    print(f"📊 Total de comentarios de entrenamiento: {total}")
    print("\n🎯 Próximos pasos:")
    print("1. Entrenar el modelo global con estos datos")
    print("2. Hacer deploy del modelo entrenado")
    print("3. Los nuevos sitios empezarán con este modelo base")

if __name__ == "__main__":
    main()
