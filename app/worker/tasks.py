import os
import base64
import io
from typing import Counter
import redis  # type: ignore
import numpy as np # type: ignore
from PIL import Image # type: ignore
from celery import Celery  # type: ignore
from deepface import DeepFace  # type: ignore
from sqlalchemy.orm import sessionmaker # type: ignore
from sqlalchemy import create_engine, exists # type: ignore
from sqlalchemy.exc import IntegrityError # type: ignore
from app.models import Emotion, Base, FinalEmotion, User, Post

redis_client = redis.Redis(host="redis", port=6379, db=0)

celery = Celery(
    "tasks",
    broker="redis://redis:6379/0",
    backend="redis://redis:6379/0",
    broker_connection_retry_on_startup=True
)

engine = create_engine("postgresql://emotion:SuperEmotionalPassword@postgres:5432/emotion_db")
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

IMAGE_SIZE = (224, 224)


@celery.task(bind=True)
def process_snapshots(self, user_id: str, post_id: str, snapshots: list):
    """
    📌 Vérifie si une émotion existe déjà pour user_id & post_id.
    - Si oui, on stoppe la tâche et on met le job en 'cancelled'.
    - Si non, on enregistre les snapshots puis on lance l'analyse IA après validation.
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
    """📂 Stocke les snapshots dans PostgreSQL après validation des clés étrangères."""
    task_id = self.request.id
    task_key = f"task:{task_id}"

    db = SessionLocal()

    try:
        user_exists = db.query(User).filter(User.user_id == user_id).first()
        if not user_exists:
            db.add(User(user_id=user_id))
            db.commit()

        post_exists = db.query(Post).filter(Post.post_id == post_id).first()
        if not post_exists:
            db.add(Post(post_id=post_id))
            db.commit()

        snapshot_objects = []
        for snapshot in snapshots:
            if snapshot.startswith("data:image"):
                snapshot = snapshot.split(",", 1)[1]

            snapshot_objects.append(
                Emotion(
                    user_id=user_id,
                    post_id=post_id,
                    snapshot=snapshot,
                    emotion=None,
                )
            )

        db.bulk_save_objects(snapshot_objects)
        db.commit()

        redis_client.hset(task_key, "status", "completed")

        analyze_snapshots_with_deepface.delay(user_id, post_id)

        return {"status": "completed", "message": "Snapshots stored in DB"}

    except IntegrityError as e:
        db.rollback()
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message", "Database integrity error: " + str(e))
        return {"status": "error", "message": "Database integrity error"}

    except Exception as e:
        db.rollback()
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message", str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()


@celery.task(bind=True)
def analyze_snapshots_with_deepface(self, user_id: str, post_id: str):
    """🔍 Analyse les snapshots avec DeepFace et met à jour les émotions en base."""
    task_id = self.request.id
    task_key = f"task:{task_id}"

    redis_client.hset(task_key, "status", "analyzing")

    db = SessionLocal()
    
    try:
        snapshots = db.query(Emotion).filter(
            Emotion.user_id == user_id,
            Emotion.post_id == post_id,
            Emotion.emotion == None
        ).all()

        if not snapshots:
            redis_client.hset(task_key, "status", "no_data")
            return {"status": "no_data", "message": "No snapshots to analyze"}

        for snap in snapshots:
            img_data = base64.b64decode(snap.snapshot)
            img = Image.open(io.BytesIO(img_data)).convert("RGB")

            try:
                result = DeepFace.analyze(img_path=np.array(img), actions=['emotion'], enforce_detection=False)
                detected_emotion = result[0]['dominant_emotion']
            except Exception as e:
                detected_emotion = "unknown"
                redis_client.hset(task_key, "error_message", f"DeepFace failed: {str(e)}")

            snap.emotion = detected_emotion
            db.add(snap)

        db.commit()

        compute_final_emotion.delay(user_id, post_id)
        redis_client.hset(task_key, "status", "submitted_final_computation")

    except Exception as e:
        db.rollback()
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message", str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
        

@celery.task(bind=True)
def compute_final_emotion(self, user_id: str, post_id: str):
    """🔍 Calcule l'émotion dominante moyenne pour un post et l'enregistre dans final_emotions."""
    task_id = self.request.id
    task_key = f"task:{task_id}"

    redis_client.hset(task_key, "status", "computing")

    db = SessionLocal()

    emotion_scores = {
        "happy": 2,
        "surprise": 1.5,
        "neutral": 0.5,
        "sad": -1,
        "fear": -1.5,
        "disgust": -2,
        "angry": -2,
    }

    try:
        emotions = db.query(Emotion.emotion).filter(
            Emotion.user_id == user_id,
            Emotion.post_id == post_id
        ).all()

        if not emotions:
            redis_client.hset(task_key, "status", "no_data")
            return {"status": "no_data", "message": "No emotions recorded for this post."}

        total_score = 0
        count = 0

        for (emotion,) in emotions:
            score = emotion_scores.get(emotion, 0)
            total_score += score
            count += 1

        if count == 0:
            final_emotion = "neutral"
        else:
            avg_score = total_score / count
            print(total_score)
            print(count)
            print(avg_score)

            if avg_score >= 1.5:
                final_emotion = "happy"
            elif avg_score >= 1:
                final_emotion = "surprise"
            elif avg_score > 0:
                final_emotion = "neutral"
            elif avg_score >= -1:
                final_emotion = "sad"
            elif avg_score >= -1.5:
                final_emotion = "fear"
            else:
                final_emotion = "angry"

        final_entry = FinalEmotion(
            user_id=user_id,
            post_id=post_id,
            emotion=final_emotion,
        )
        db.add(final_entry)
        db.commit()

        redis_client.hset(task_key, "status", "completed")
        return {"status": "completed", "message": f"Final emotion computed: {final_emotion}"}

    except Exception as e:
        db.rollback()
        redis_client.hset(task_key, "status", "error")
        redis_client.hset(task_key, "error_message", str(e))
        return {"status": "error", "message": str(e)}

    finally:
        db.close()
