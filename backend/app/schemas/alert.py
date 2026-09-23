from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class AlertResponse(BaseModel):
    id: int
    alert_type: str
    message: str
    latitude: float
    longitude: float
    severity: Optional[str]
    issue_id: Optional[int]
    created_at: datetime
    expires_at: Optional[datetime]

    class Config:
        from_attributes = True