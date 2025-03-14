from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from app.api.routes import home, get_snapshot, get_emotions

app = FastAPI(title="Emotion API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home.router, tags=["Home"])
app.include_router(get_snapshot.router, tags=["Get Snapshot"])
app.include_router(get_emotions.router, tags=["Get Emotions"])