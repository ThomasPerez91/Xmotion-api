from fastapi import APIRouter  # type: ignore

router = APIRouter()


@router.get("/")
async def home():
    return {"message": "Hello, World!"}
