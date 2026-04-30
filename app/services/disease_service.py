from sqlalchemy.orm import Session
from typing import Optional

from app.models.disease import Disease
from app.schemas.disease import DiseaseInfoResponse


def get_disease_info_by_slug(slug: str, db: Session) -> Optional[DiseaseInfoResponse]:
    disease = db.query(Disease).filter(Disease.slug == slug.lower()).first()
    if disease is None:
        return None

    recommendations = [
        recommendation.recommendation
        for recommendation in sorted(disease.recommendations, key=lambda item: item.order_index)
    ]

    return DiseaseInfoResponse(
        name=disease.name,
        slug=disease.slug,
        description=disease.description,
        symptoms=disease.symptoms,
        causes=disease.causes,
        prevention=disease.prevention,
        severity_level=disease.severity_level,
        recommendations=recommendations,
        disclaimer=disease.disclaimer,
    )
