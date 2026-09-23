from typing import Optional

from pydantic import BaseModel, Field


class RouteBase(BaseModel):
    name: str = Field(..., min_length=1)
    start_point: str = Field(..., min_length=1)
    end_point: str = Field(..., min_length=1)
    status: str = "active"


class RouteCreate(RouteBase):
    pass


class RouteRead(RouteBase):
    id: Optional[int] = None
