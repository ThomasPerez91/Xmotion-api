from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import DATABASE_URL

# 🔗 Connexion PostgreSQL via SQLAlchemy
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# ✅ Fonction pour récupérer une session (utilisée dans FastAPI)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
