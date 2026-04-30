from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.disease import DiseaseInfoResponse
from app.services.disease_service import get_disease_info_by_slug

router = APIRouter()

@router.get("/{slug}", response_model=DiseaseInfoResponse)
def get_disease_info(slug: str, db: Session = Depends(get_db)):
    data = get_disease_info_by_slug(slug, db)
    if not data:
        raise HTTPException(status_code=404, detail="Disease not found")
    return data
