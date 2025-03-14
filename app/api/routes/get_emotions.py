from fastapi import APIRouter, Depends, Query, HTTPException  # type: ignore
from sqlalchemy.orm import Session  # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from sqlalchemy import create_engine, func, text # type: ignore
from typing import Optional, List
from app.models import FinalEmotion, Emotion  # Ajout du modèle Emotion

# 🔗 Connexion directe à PostgreSQL
engine = create_engine("postgresql://emotion:SuperEmotionalPassword@postgres:5432/emotion_db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

router = APIRouter()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@router.get("/emotions")
def get_final_emotion(
    user_id: Optional[str] = Query(None, description="Filtrer par user_id"),
    post_id: Optional[str] = Query(None, description="Filtrer par post_id"),
    db: Session = Depends(get_db),
):
    """
    🔥 Récupère les émotions finales avec le nombre de snapshots utilisés :
    - SANS paramètres : tout récupérer, trié par `post_id`.
    - AVEC `user_id` : récupère toutes les émotions de l'utilisateur.
    - AVEC `post_id` : récupère toutes les émotions du post.
    - AVEC `user_id` + `post_id` : récupère une seule ligne spécifique.
    """

    query = db.query(
        FinalEmotion.id,
        FinalEmotion.user_id,
        FinalEmotion.post_id,
        FinalEmotion.emotion,
        FinalEmotion.created_at,
        func.count(Emotion.snapshot).label("snapshot_count")
    ).join(Emotion, (FinalEmotion.user_id == Emotion.user_id) & (FinalEmotion.post_id == Emotion.post_id))

    if user_id:
        query = query.filter(FinalEmotion.user_id == user_id)
    if post_id:
        query = query.filter(FinalEmotion.post_id == post_id)

    query = query.group_by(FinalEmotion.id, FinalEmotion.user_id, FinalEmotion.post_id, FinalEmotion.emotion, FinalEmotion.created_at)
    emotions = query.order_by(FinalEmotion.post_id).all()

    return [
        {
            "user_id": user_id,
            "post_id": post_id,
            "emotion": emotion,
            "created_at": created_at,
            "snapshot_count": snapshot_count
        }
        for _, user_id, post_id, emotion, created_at, snapshot_count in emotions
    ]

@router.get("/emotion")
def get_emotions(
    user_id: str = Query(..., description="User ID obligatoire"),
    post_id: str = Query(..., description="Post ID obligatoire"),
    db: Session = Depends(get_db),
):
    """
    🔥 Récupère tous les snapshots et leurs émotions associées pour un utilisateur et un post spécifiques.
    - `user_id` et `post_id` sont requis.
    - Renvoie une erreur si aucun enregistrement trouvé.
    - Retourne un JSON avec chaque snapshot (Base64) et son émotion associée.
    """

    snapshots = db.query(Emotion.snapshot, Emotion.emotion).filter(
        Emotion.user_id == user_id,
        Emotion.post_id == post_id
    ).all()

    if not snapshots:
        raise HTTPException(status_code=404, detail="Aucune donnée trouvée pour cet utilisateur et ce post.")

    return [{"snapshot": snapshot, "emotion": emotion} for snapshot, emotion in snapshots]

@router.get("/truncate")
def truncate_tables(db: Session = Depends(get_db)):
    """
    🚨 Supprime toutes les données des tables `users`, `posts`, `emotions`, et `final_emotions`.
    """
    try:
        db.execute(text("TRUNCATE TABLE users, posts, emotions, final_emotions RESTART IDENTITY CASCADE"))
        db.commit()
        return {"message": "Toutes les tables ont été vidées avec succès."}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Erreur lors de la suppression des données: {str(e)}")