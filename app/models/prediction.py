from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text
from datetime import datetime, timezone
from app.models.base import Base

class Prediction(Base):
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"))
    image_name = Column(String)
    predicted_class = Column(String, nullable=False)
    confidence = Column(Float, nullable=False)
    scores_json = Column(Text)  # JSON string
    model_version = Column(String)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
