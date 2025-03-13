import os
import base64
import json
import redis  # type: ignore
from celery import Celery  # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from sqlalchemy import create_engine, exists # type: ignore
from sqlalchemy.exc import IntegrityError # type: ignore 
from app.models import Emotion, User, Post

# 🔥 Initialisation de Redis
redis_client = redis.Redis(host="redis", port=6379, db=0)

# 🚀 Configuration de Celery
celery = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    broker_connection_retry_on_startup=True
)

# 🔗 Connexion à PostgreSQL via SQLAlchemy
engine = create_engine("postgresql://emotion:SuperEmotionalPassword@postgres:5432/emotion_db"
                       )
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@celery.task(bind=True)
def process_snapshots(self, user_id: str, post_id: str, snapshots: list):
    """
    1️⃣ Vérifie dans la DB si une émotion existe déjà pour user_id & post_id.
    2️⃣ Si oui, stoppe la tâche et met le job en 'cancelled'.
    3️⃣ Si non, lance `register_snapshot` pour enregistrer les données.
    """
    task_id = self.request.id
    task_key = f"task:{task_id}"

    redis_client.hset(task_key, "status", "processing")

    db = SessionLocal()

    try:
        already_exists = db.query(exists().where(
            (Emotion.user_id == user_id) & (Emotion.post_id == post_id))).scalar()

        if already_exists:
            redis_client.hset(task_key, "status", "cancelled")
            db.close()
            return {"status": "cancelled", "reason": "Emotion already recorded for this user and post."}

        # ✅ Si aucune émotion n’existe, on enregistre les snapshots
        register_snapshot.delay(user_id, post_id, snapshots)
        redis_client.hset(task_key, "status", "submitted")

    except Exception as e:
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message", str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@celery.task(bind=True)
def register_snapshot(self, user_id: str, post_id: str, snapshots: list):
    """Stocke les snapshots dans PostgreSQL après validation des clés étrangères."""
    task_id = self.request.id
    task_key = f"task:{task_id}"

    db = SessionLocal()

    try:
        # 🔍 Vérifier si `user_id` existe déjà
        user_exists = db.query(User).filter(User.user_id == user_id).first()
        if not user_exists:
            db.add(User(user_id=user_id))
            db.commit()  # ✅ Commit immédiat pour éviter les erreurs FK

        # 🔍 Vérifier si `post_id` existe déjà
        post_exists = db.query(Post).filter(Post.post_id == post_id).first()
        if not post_exists:
            db.add(Post(post_id=post_id))
            db.commit()  # ✅ Commit immédiat pour éviter les erreurs FK

        # 📂 Insérer les snapshots
        snapshot_objects = []
        for snapshot in snapshots:
            if snapshot.startswith("data:image"):
                # 🔹 Supprimer le préfixe Base64
                snapshot = snapshot.split(",", 1)[1]

            snapshot_objects.append(
                Emotion(
                    user_id=user_id,
                    post_id=post_id,
                    snapshot=snapshot,
                    emotion=None,  # L'émotion sera analysée plus tard
                )
            )

        db.bulk_save_objects(snapshot_objects)  # ✅ Ajout optimisé
        db.commit()

        redis_client.hset(task_key, "status", "completed")
        return {"status": "completed", "message": "Snapshots stored in DB"}

    except IntegrityError as e:
        db.rollback()
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message",
                          "Database integrity error: " + str(e))
        return {"status": "error", "message": "Database integrity error"}

    except Exception as e:
        db.rollback()
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message", str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
