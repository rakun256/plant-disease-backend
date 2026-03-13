from pydantic import BaseModel
from typing import List

class DiseaseInfoResponse(BaseModel):
    name: str
    slug: str
    description: str
    recommendations: List[str]
    disclaimer: str
