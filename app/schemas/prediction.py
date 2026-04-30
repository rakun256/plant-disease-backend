from pydantic import BaseModel
from pydantic import field_validator
from typing import Dict, List, Optional
from datetime import datetime
from app.core.constants import SUPPORTED_CLASSES

class PredictionResponse(BaseModel):
    model_version: str
    predicted_class: str
    confidence: float
    scores: Dict[str, float]
    supported_classes: List[str]
    warning: str

class PredictionHistoryResponse(BaseModel):
    id: int
    image_name: str
    predicted_class: str
    confidence: float
    model_version: str
    created_at: datetime
    scores: Dict[str, float]

    class Config:
        from_attributes = True

class PredictionFeedbackCreate(BaseModel):
    is_correct: bool
    corrected_class: Optional[str] = None
    note: Optional[str] = None

    @field_validator("corrected_class")
    @classmethod
    def validate_corrected_class(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return value
        normalized_value = value.strip().lower()
        if normalized_value not in SUPPORTED_CLASSES:
            supported_classes = ", ".join(SUPPORTED_CLASSES)
            raise ValueError(f"corrected_class must be one of: {supported_classes}")
        return normalized_value

class PredictionFeedbackResponse(BaseModel):
    id: int
    prediction_id: int
    user_id: int
    is_correct: bool
    corrected_class: Optional[str] = None
    note: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True
