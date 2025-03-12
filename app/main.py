from fastapi import FastAPI  # type: ignore
from fastapi.middleware.cors import CORSMiddleware  # type: ignore
from app.api.routes import home, get_snapshot

app = FastAPI(title="Emotion API")

# ✅ Autoriser CORS pour le front React
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(home.router, tags=["Home"])
app.include_router(get_snapshot.router, tags=["Get Snapshot"])
