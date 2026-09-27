from datetime import datetime
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field, field_validator


VALID_EVENT_TYPES = {
    "pothole",
    "waterlogging",
    "accident",
    "traffic_violation",
    "helmet_violation",
    "triple_riding",
    "rash_driving",
    "traffic_bottleneck",
    "high_vehicle_density",
    "pedestrian_risk",
    "road_damage",
    "missing_divider",
    "missing_zebra_crossing",
    "traffic_sign_issue",
    "vulnerable_pedestrian",
    "other",
}

class EventCreate(BaseModel):
    event_type: str
    confidence: Optional[float] = Field(default=None, ge=0, le=1)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    timestamp: Optional[datetime] = None
    bus_id: Optional[int] = None
    camera_id: Optional[int] = None
    metadata: Optional[Dict[str, Any]] = None
    severity: Optional[str] = None
    registration_number: Optional[str] = None

    @field_validator("event_type")
    @classmethod
    def validate_event_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower().replace(" ", "_")
        normalized = {"damaged_road": "road_damage", "without_helmet": "helmet_violation",
                      "congestion": "high_vehicle_density", "bottleneck": "traffic_bottleneck"}.get(normalized, normalized)
        if normalized not in VALID_EVENT_TYPES:
            raise ValueError(
                "Unsupported event type. Must be one of: "
                + ", ".join(sorted(VALID_EVENT_TYPES))
            )
        return normalized

    @field_validator("timestamp")
    @classmethod
    def utc_timestamp(cls, value):
        from datetime import timezone
        return value.astimezone(timezone.utc).replace(tzinfo=None) if value and value.tzinfo else value

    @field_validator("severity")
    @classmethod
    def normalize_severity(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        return str(value).strip().lower()


class EventResponse(BaseModel):
    id: int
    event_type: str
    confidence: Optional[float]
    latitude: float
    longitude: float
    timestamp: datetime
    bus_id: Optional[int]
    camera_id: Optional[int]
    registration_number: Optional[str]
    severity: Optional[str]
    status: str
    metadata: Optional[Dict[str, Any]] = None

    class Config:
        from_attributes = True
