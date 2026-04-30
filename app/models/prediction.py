from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_name = Column(String)
    predicted_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    inference_time_ms = Column(Float)
    is_low_confidence = Column(Boolean, nullable=False, default=False)
    image_width = Column(Integer)
    image_height = Column(Integer)
    image_brightness_score = Column(Float)
    image_contrast_score = Column(Float)
    image_blur_score = Column(Float)
    image_quality_score = Column(Float)
    is_quality_acceptable = Column(Boolean)
    quality_warnings_json = Column(Text)
    scores_json = Column(Text)  # JSON string
    model_version = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    feedback_records = relationship("PredictionFeedback", back_populates="prediction")
