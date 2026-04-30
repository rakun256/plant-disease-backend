from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.models.prediction import Prediction
from app.models.user import User
from app.schemas.analytics import AnalyticsSummaryResponse, LatestPredictionSummary


def get_user_analytics_summary(user: User, db: Session) -> AnalyticsSummaryResponse:
    total_predictions = (
        db.query(func.count(Prediction.id))
        .filter(Prediction.user_id == user.id)
        .scalar()
    )

    if total_predictions == 0:
        return AnalyticsSummaryResponse(
            total_predictions=0,
            class_distribution={},
            average_confidence=None,
            low_confidence_count=0,
            low_confidence_rate=0,
            average_inference_time_ms=None,
            average_image_quality_score=None,
            low_quality_count=0,
            low_quality_rate=0,
            latest_prediction=None,
            model_version_distribution={},
        )

    (
        average_confidence,
        low_confidence_count,
        average_inference_time_ms,
        average_image_quality_score,
        low_quality_count,
    ) = (
        db.query(
            func.avg(Prediction.confidence),
            func.sum(case((Prediction.is_low_confidence == True, 1), else_=0)),
            func.avg(Prediction.inference_time_ms),
            func.avg(Prediction.image_quality_score),
            func.sum(case((Prediction.is_quality_acceptable == False, 1), else_=0)),
        )
        .filter(Prediction.user_id == user.id)
        .one()
    )

    class_distribution = {
        predicted_class: count
        for predicted_class, count in (
            db.query(Prediction.predicted_class, func.count(Prediction.id))
            .filter(Prediction.user_id == user.id)
            .group_by(Prediction.predicted_class)
            .all()
        )
    }

    model_version_distribution = {
        model_version or "unknown": count
        for model_version, count in (
            db.query(Prediction.model_version, func.count(Prediction.id))
            .filter(Prediction.user_id == user.id)
            .group_by(Prediction.model_version)
            .all()
        )
    }

    latest_prediction = (
        db.query(Prediction)
        .filter(Prediction.user_id == user.id)
        .order_by(Prediction.created_at.desc(), Prediction.id.desc())
        .first()
    )

    low_confidence_count = int(low_confidence_count or 0)
    low_quality_count = int(low_quality_count or 0)

    return AnalyticsSummaryResponse(
        total_predictions=total_predictions,
        class_distribution=class_distribution,
        average_confidence=float(average_confidence) if average_confidence is not None else None,
        low_confidence_count=low_confidence_count,
        low_confidence_rate=low_confidence_count / total_predictions,
        average_inference_time_ms=(
            round(float(average_inference_time_ms), 2) if average_inference_time_ms is not None else None
        ),
        average_image_quality_score=(
            round(float(average_image_quality_score), 2) if average_image_quality_score is not None else None
        ),
        low_quality_count=low_quality_count,
        low_quality_rate=low_quality_count / total_predictions,
        latest_prediction=(
            LatestPredictionSummary.model_validate(latest_prediction)
            if latest_prediction is not None
            else None
        ),
        model_version_distribution=model_version_distribution,
    )
