from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class ViolationBase(BaseModel):
    violation_type: str
    severity: Optional[str] = "medium"
    status: Optional[str] = "open"

    vehicle_number: Optional[str] = None
    confidence: Optional[float] = None

    latitude: Optional[float] = None
    longitude: Optional[float] = None

    description: Optional[str] = None


class ViolationCreate(ViolationBase):
    pass


class ViolationResponse(ViolationBase):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)