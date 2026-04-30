from pydantic import BaseModel
from typing import List, Optional

class DiseaseInfoResponse(BaseModel):
    name: str
    slug: str
    description: str
    symptoms: Optional[str] = None
    causes: Optional[str] = None
    prevention: Optional[str] = None
    severity_level: Optional[str] = None
    recommendations: List[str]
    disclaimer: str
