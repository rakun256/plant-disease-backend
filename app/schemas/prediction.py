from pydantic import BaseModel
from typing import Dict, List, Any
from datetime import datetime

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
