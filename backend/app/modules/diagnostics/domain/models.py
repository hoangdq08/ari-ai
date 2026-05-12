from pydantic import BaseModel
from typing import Optional

class DiagnosticResultEntity(BaseModel):
    disease_name: str
    confidence: float
    treatment: str
    preventive_measures: Optional[str] = None
