from fastapi import APIRouter, File, UploadFile, Depends, Form
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.services.prediction_service import process_prediction
from app.schemas.prediction import PredictionResponse
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=PredictionResponse, summary="Predict disease from leaf image")
async def predict_image(
    file: UploadFile = File(...),
    save_result: bool = Form(default=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image of an apple leaf to get a disease prediction.
    Supported types: JPEG, PNG. Max size: 5MB
    """
    return await process_prediction(file, save_result, current_user, db)
