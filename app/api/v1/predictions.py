from fastapi import APIRouter, File, UploadFile, Depends, Form, status
from sqlalchemy.orm import Session
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.services.prediction_service import process_prediction
from app.services.prediction_feedback_service import create_prediction_feedback
from app.schemas.prediction import PredictionFeedbackCreate, PredictionFeedbackResponse, PredictionResponse
from app.models.user import User

router = APIRouter()

@router.post("/", response_model=PredictionResponse, summary="Predict disease from leaf image")
async def predict_image(
    file: UploadFile = File(...),
    save_result: bool = Form(default=True),
    include_explanation: bool = Form(default=False),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Upload an image of an apple leaf to get a disease prediction.
    Supported types: JPEG, PNG. Max size: 5MB
    """
    return await process_prediction(file, save_result, current_user, db, include_explanation)

@router.post(
    "/{prediction_id}/feedback",
    response_model=PredictionFeedbackResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Submit feedback for a prediction",
)
def submit_prediction_feedback(
    prediction_id: int,
    feedback_in: PredictionFeedbackCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit feedback for a previous prediction owned by the authenticated user.
    """
    return create_prediction_feedback(prediction_id, feedback_in, current_user, db)
