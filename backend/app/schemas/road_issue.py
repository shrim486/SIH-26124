from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class RoadIssueResponse(BaseModel):
    id: int
    issue_type: str
    latitude: float
    longitude: float
    confidence: Optional[float]
    severity: Optional[str]
    status: str
    first_detected: datetime
    last_detected: datetime

    class Config:
        from_attributes = True