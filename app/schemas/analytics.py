from datetime import datetime
from typing import Dict, Optional

from pydantic import BaseModel, ConfigDict


class LatestPredictionSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    predicted_class: str
    confidence: float
    created_at: datetime


class AnalyticsSummaryResponse(BaseModel):
    total_predictions: int
    class_distribution: Dict[str, int]
    average_confidence: Optional[float] = None
    low_confidence_count: int
    low_confidence_rate: float
    average_inference_time_ms: Optional[float] = None
    average_image_quality_score: Optional[float] = None
    low_quality_count: int
    low_quality_rate: float
    latest_prediction: Optional[LatestPredictionSummary] = None
    model_version_distribution: Dict[str, int]
