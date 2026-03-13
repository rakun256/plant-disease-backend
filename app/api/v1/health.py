from fastapi import APIRouter
from app.core.config import settings
from app.ml.model_loader import ml_manager

router = APIRouter()

@router.get("/")
def health_check():
    return {
        "status": "ok",
        "model_loaded": ml_manager.is_loaded,
        "version": settings.APP_VERSION
    }
