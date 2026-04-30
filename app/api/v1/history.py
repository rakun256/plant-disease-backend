from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.prediction import PredictionHistoryResponse
import json

router = APIRouter()

@router.get("/", response_model=List[PredictionHistoryResponse])
def get_prediction_history(
    skip: int = 0, limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = db.query(Prediction).filter(Prediction.user_id == current_user.id).offset(skip).limit(limit).all()
    
    results = []
    for p in predictions:
        results.append(PredictionHistoryResponse(
            id=p.id,
            image_name=p.image_name,
            predicted_class=p.predicted_class,
            confidence=p.confidence,
            inference_time_ms=p.inference_time_ms,
            is_low_confidence=p.is_low_confidence,
            model_version=p.model_version,
            created_at=p.created_at,
            scores=json.loads(p.scores_json) if p.scores_json else {}
        ))
    return results
