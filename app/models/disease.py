from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from app.models.base import Base


class Disease(Base):
    __tablename__ = "diseases"

    id = Column(Integer, primary_key=True, index=True)
    slug = Column(String, unique=True, nullable=False)
    name = Column(String, nullable=False)
    description = Column(Text, nullable=False)
    symptoms = Column(Text)
    causes = Column(Text)
    prevention = Column(Text)
    severity_level = Column(String)
    disclaimer = Column(Text, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    recommendations = relationship(
        "DiseaseRecommendation",
        back_populates="disease",
        cascade="all, delete-orphan",
        order_by="DiseaseRecommendation.order_index",
    )


class DiseaseRecommendation(Base):
    __tablename__ = "disease_recommendations"

    id = Column(Integer, primary_key=True, index=True)
    disease_id = Column(Integer, ForeignKey("diseases.id"), nullable=False, index=True)
    recommendation = Column(Text, nullable=False)
    order_index = Column(Integer, default=0)

    disease = relationship("Disease", back_populates="recommendations")
