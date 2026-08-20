from pydantic import BaseModel, Field
from typing import List, Optional
from datetime import datetime


class AnalysisObject(BaseModel):
    name: str
    confidence: float
    description: Optional[str] = None


class ImageAnalysis(BaseModel):
    id: str
    filename: str
    uploaded_at: datetime
    description: str
    objects: List[AnalysisObject] = Field(default_factory=list)
    sentiment: str = "neutral"
    tags: List[str] = Field(default_factory=list)
    extracted_text: str = ""
    processing_time_ms: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    image_url: str


class AnalysisRequest(BaseModel):
    detail_level: str = "medium"  # simple, medium, detailed
    language: str = "en"


class BatchAnalysisRequest(BaseModel):
    detail_level: str = "medium"
    language: str = "en"


class BatchResult(BaseModel):
    total: int
    successful: int
    results: List[dict]
