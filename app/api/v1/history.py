from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from typing import List
from app.db.database import get_db
from app.api.dependencies import get_current_user
from app.models.user import User
from app.models.prediction import Prediction
from app.schemas.prediction import ImageQualityResponse, PredictionHistoryResponse
from app.services.input_assessment_service import build_input_assessment
import json

router = APIRouter()

@router.get("/", response_model=List[PredictionHistoryResponse])
def get_prediction_history(
    skip: int = 0, limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    predictions = (
        db.query(Prediction)
        .filter(Prediction.user_id == current_user.id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )
    
    results = []
    for p in predictions:
        image_quality = _build_image_quality_response(p)
        results.append(PredictionHistoryResponse(
            id=p.id,
            image_name=p.image_name,
            predicted_class=p.predicted_class,
            confidence=p.confidence,
            inference_time_ms=p.inference_time_ms,
            is_low_confidence=p.is_low_confidence,
            model_version=p.model_version,
            created_at=p.created_at,
            scores=json.loads(p.scores_json) if p.scores_json else {},
            image_quality=image_quality,
            input_assessment=build_input_assessment(p.is_low_confidence, image_quality)
        ))
    return results


def _build_image_quality_response(prediction: Prediction):
    if prediction.image_quality_score is None:
        return None

    return ImageQualityResponse(
        width=prediction.image_width or 0,
        height=prediction.image_height or 0,
        brightness_score=prediction.image_brightness_score or 0,
        contrast_score=prediction.image_contrast_score or 0,
        blur_score=prediction.image_blur_score or 0,
        quality_score=prediction.image_quality_score,
        is_quality_acceptable=(
            prediction.is_quality_acceptable if prediction.is_quality_acceptable is not None else True
        ),
        quality_warnings=json.loads(prediction.quality_warnings_json) if prediction.quality_warnings_json else [],
    )
