from typing import Literal
from pydantic import BaseModel, Field, ConfigDict


class JourneyPoint(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')
    latitude: float = Field(ge=-85, le=85, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    label: str = Field(default='', max_length=250)
    dwell_minutes: int = Field(default=0, ge=0, le=120)


class JourneyRequest(BaseModel):
    model_config = ConfigDict(extra='forbid')
    origin: JourneyPoint
    destination: JourneyPoint
    stops: list[JourneyPoint] = Field(default_factory=list, max_length=3)
    preference: Literal['balanced', 'fastest', 'lower_risk'] = 'balanced'
    max_extra_minutes: int = Field(default=15, ge=0, le=60)
    include_assigned: bool = False
