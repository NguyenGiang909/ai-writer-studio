from fastapi import APIRouter
from app.core.config import settings
router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok", "build_id": settings.build_id,
            "environment": settings.environment}
