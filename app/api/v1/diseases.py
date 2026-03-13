from fastapi import APIRouter, HTTPException
from app.schemas.disease import DiseaseInfoResponse

router = APIRouter()

DISEASES_DB = {
    "healthy": {
        "name": "Healthy Apple Leaf", "slug": "healthy",
        "description": "The leaf shows no signs of disease.",
        "recommendations": ["Maintain a regular spray schedule.", "Ensure proper watering."],
        "disclaimer": "This is an AI prediction, consult an agricultural expert."
    },
    "rust": {
        "name": "Cedar Apple Rust", "slug": "rust",
        "description": "A fungal disease causing yellow-orange spots.",
        "recommendations": ["Apply appropriate fungicide.", "Remove nearby cedar rust galls."],
        "disclaimer": "This is an AI prediction, consult an agricultural expert."
    },
    "scab": {
        "name": "Apple Scab", "slug": "scab",
        "description": "Fungal disease causing olive-green to black spots.",
        "recommendations": ["Apply fungicide preventatively.", "Clear fallen infected leaves."],
        "disclaimer": "This is an AI prediction, consult an agricultural expert."
    }
}

@router.get("/{slug}", response_model=DiseaseInfoResponse)
def get_disease_info(slug: str):
    data = DISEASES_DB.get(slug.lower())
    if not data:
        raise HTTPException(status_code=404, detail="Disease not found")
    return data
