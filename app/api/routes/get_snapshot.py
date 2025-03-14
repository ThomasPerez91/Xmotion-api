from fastapi import APIRouter, HTTPException  # type: ignore
from pydantic import BaseModel  # type: ignore
from uuid import UUID
from app.worker.tasks import process_snapshots

router = APIRouter()

class SnapshotRequest(BaseModel):
    user_id: str
    post_id: str
    snapshots: list[str]


@router.post("/snapshots")
async def receive_snapshots(request: SnapshotRequest):
    """
    Endpoint pour recevoir les snapshots et envoyer la tâche à Celery.
    """
    if not request.snapshots:
        raise HTTPException(status_code=400, detail="Aucun snapshot fourni.")

    task = process_snapshots.delay(
        str(request.user_id), str(request.post_id), request.snapshots)

    return {"message": "Tâche en cours", "task_id": task.id}
