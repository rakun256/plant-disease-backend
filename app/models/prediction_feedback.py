from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint, func
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
from app.models.base import Base

class PredictionFeedback(Base):
    __tablename__ = "prediction_feedback"
    __table_args__ = (
        UniqueConstraint("user_id", "prediction_id", name="uq_prediction_feedback_user_prediction"),
    )

    id = Column(Integer, primary_key=True, index=True)
    prediction_id = Column(Integer, ForeignKey("predictions.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    is_correct = Column(Boolean, nullable=False)
    corrected_class = Column(String)
    note = Column(Text)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), server_default=func.now())

    prediction = relationship("Prediction", back_populates="feedback_records")
    user = relationship("User", back_populates="feedback_records")
