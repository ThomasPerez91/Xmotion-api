import os
from dotenv import load_dotenv  # type: ignore

# Charger le fichier .env
load_dotenv()


class Config:
    APP_NAME = os.getenv("APP_NAME", "emotion_api")
    APP_ENV = os.getenv("APP_ENV", "development")
    APP_DEBUG = os.getenv("APP_DEBUG", "True") == "True"
    APP_HOST = os.getenv("APP_HOST", "0.0.0.0")
    APP_PORT = int(os.getenv("APP_PORT", 8000))

    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

    SNAPSHOT_PATH = os.getenv("SNAPSHOT_PATH", "/snapshots")
    DATABASE_URL = os.getenv("DATABASE_URL", "")


config = Config()
