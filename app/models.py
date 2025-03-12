from sqlalchemy import Column, String, Text, ForeignKey, TIMESTAMP, func, Integer  # type: ignore
from sqlalchemy.ext.declarative import declarative_base  # type: ignore

Base = declarative_base()


class User(Base):
    __tablename__ = "users"

    user_id = Column(String(255), primary_key=True)


class Post(Base):
    __tablename__ = "posts"

    post_id = Column(String(255), primary_key=True)


class Emotion(Base):
    __tablename__ = "emotions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey(
        "users.user_id", ondelete="CASCADE"), nullable=False)
    post_id = Column(String(255), ForeignKey(
        "posts.post_id", ondelete="CASCADE"), nullable=False)
    snapshot = Column(Text, nullable=False)  # Stocke l’image en Base64
    emotion = Column(String(100), nullable=True)  # L'émotion détectée
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())


class FinalEmotion(Base):
    __tablename__ = "final_emotions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(String(255), ForeignKey(
        "users.user_id", ondelete="CASCADE"), nullable=False)
    post_id = Column(String(255), ForeignKey(
        "posts.post_id", ondelete="CASCADE"), nullable=False)
    # Emotion finale après analyse
    emotion = Column(String(100), nullable=True)
    created_at = Column(TIMESTAMP, server_default=func.now())
    updated_at = Column(
        TIMESTAMP, server_default=func.now(), onupdate=func.now())
