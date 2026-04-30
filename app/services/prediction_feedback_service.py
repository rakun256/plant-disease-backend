from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.models.prediction_feedback import PredictionFeedback
from app.models.user import User
from app.schemas.prediction import PredictionFeedbackCreate


def create_prediction_feedback(
    prediction_id: int,
    feedback_in: PredictionFeedbackCreate,
    user: User,
    db: Session,
) -> PredictionFeedback:
    prediction = db.query(Prediction).filter(Prediction.id == prediction_id).first()
    if prediction is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Prediction not found.",
        )

    if prediction.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You can only submit feedback for your own predictions.",
        )

    existing_feedback = (
        db.query(PredictionFeedback)
        .filter(
            PredictionFeedback.prediction_id == prediction_id,
            PredictionFeedback.user_id == user.id,
        )
        .first()
    )
    if existing_feedback:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already exists for this prediction.",
        )

    feedback = PredictionFeedback(
        prediction_id=prediction_id,
        user_id=user.id,
        is_correct=feedback_in.is_correct,
        corrected_class=feedback_in.corrected_class,
        note=feedback_in.note,
    )
    db.add(feedback)

    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Feedback already exists for this prediction.",
        )

    db.refresh(feedback)
    return feedback
