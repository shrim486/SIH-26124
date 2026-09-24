from math import radians, sin, cos, sqrt, atan2

from fastapi import APIRouter, Depends, Query, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.alert import Alert
from app.models.event import Event
from app.models.road_issue import RoadIssue


router = APIRouter(
    prefix="/user",
    tags=["Citizen"],
)


# ============================================================
# MODELS
# ============================================================

class LocationPoint(BaseModel):
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)


class RouteRequest(BaseModel):
    origin: LocationPoint
    destination: LocationPoint


# ============================================================
# DISTANCE
# ============================================================

def haversine_km(
    lat1: float,
    lon1: float,
    lat2: float,
    lon2: float,
) -> float:

    r = 6371.0

    lat1_rad = radians(lat1)
    lat2_rad = radians(lat2)

    dlat = radians(lat2 - lat1)
    dlon = radians(lon2 - lon1)

    a = (
        sin(dlat / 2) ** 2
        + cos(lat1_rad)
        * cos(lat2_rad)
        * sin(dlon / 2) ** 2
    )

    c = 2 * atan2(
        sqrt(a),
        sqrt(1 - a),
    )

    return r * c


# ============================================================
# CITIZEN DASHBOARD
# ============================================================

@router.get("/dashboard")
def get_user_dashboard(
    db: Session = Depends(get_db),
):

    total_alerts = db.query(Alert).count()

    open_issues = (
        db.query(RoadIssue)
        .filter(RoadIssue.status == "open")
        .count()
    )

    resolved_issues = (
        db.query(RoadIssue)
        .filter(RoadIssue.status == "resolved")
        .count()
    )

    potholes = (
        db.query(Event)
        .filter(Event.event_type == "pothole")
        .count()
    )

    waterlogging = (
        db.query(Event)
        .filter(Event.event_type == "waterlogging")
        .count()
    )

    accidents = (
        db.query(Event)
        .filter(Event.event_type == "accident")
        .count()
    )

    recent_alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(20)
        .all()
    )

    return {
        "statistics": {
            "total_alerts": total_alerts,
            "open_issues": open_issues,
            "resolved_issues": resolved_issues,
            "potholes": potholes,
            "waterlogging": waterlogging,
            "accidents": accidents,
        },
        "recent_alerts": recent_alerts,
    }


# ============================================================
# CITIZEN MAP EVENTS
# ============================================================

@router.get("/map-events")
def get_user_map_events(
    db: Session = Depends(get_db),
):

    events = (
        db.query(Event)
        .filter(
            Event.latitude.isnot(None),
            Event.longitude.isnot(None),
        )
        .order_by(Event.timestamp.desc())
        .limit(500)
        .all()
    )

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "confidence": event.confidence,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "timestamp": event.timestamp,
            "bus_id": event.bus_id,
            "camera_id": event.camera_id,
            "registration_number": event.registration_number,
            "severity": event.severity,
            "status": event.status,
            "event_metadata": event.event_metadata,
        }
        for event in events
    ]


# ============================================================
# CITIZEN ALERTS
# ============================================================

@router.get("/alerts")
def get_user_alerts(
    db: Session = Depends(get_db),
):

    return (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .limit(50)
        .all()
    )


# ============================================================
# NEARBY ALERTS
# ============================================================

@router.get("/nearby-alerts")
def get_nearby_alerts(
    latitude: float = Query(
        ...,
        ge=-90,
        le=90,
    ),
    longitude: float = Query(
        ...,
        ge=-180,
        le=180,
    ),
    radius_km: float = Query(
        5.0,
        ge=0.1,
        le=50.0,
    ),
    db: Session = Depends(get_db),
):

    results = []

    # --------------------------------------------------------
    # ROAD ISSUES
    # --------------------------------------------------------

    for issue in db.query(RoadIssue).all():

        if issue.latitude is None or issue.longitude is None:
            continue

        distance = haversine_km(
            latitude,
            longitude,
            issue.latitude,
            issue.longitude,
        )

        if distance <= radius_km:

            results.append(
                {
                    "type": issue.issue_type,
                    "latitude": issue.latitude,
                    "longitude": issue.longitude,
                    "severity": issue.severity or "medium",
                    "message": "Road hazard ahead",
                    "distance_km": round(
                        distance,
                        2,
                    ),
                }
            )

    # --------------------------------------------------------
    # ALERTS
    # --------------------------------------------------------

    for alert in db.query(Alert).all():

        if alert.latitude is None or alert.longitude is None:
            continue

        distance = haversine_km(
            latitude,
            longitude,
            alert.latitude,
            alert.longitude,
        )

        if distance <= radius_km:

            results.append(
                {
                    "type": alert.alert_type,
                    "latitude": alert.latitude,
                    "longitude": alert.longitude,
                    "severity": alert.severity or "medium",
                    "message": alert.message,
                    "distance_km": round(
                        distance,
                        2,
                    ),
                }
            )

    return results


# ============================================================
# ROUTE
# ============================================================

@router.post(
    "/route",
    status_code=status.HTTP_200_OK,
)
def create_user_route(
    payload: RouteRequest,
):

    origin = payload.origin
    destination = payload.destination

    distance_km = haversine_km(
        origin.latitude,
        origin.longitude,
        destination.latitude,
        destination.longitude,
    )

    route = [
        {
            "latitude": origin.latitude,
            "longitude": origin.longitude,
        },
        {
            "latitude": (
                origin.latitude
                + destination.latitude
            ) / 2,
            "longitude": (
                origin.longitude
                + destination.longitude
            ) / 2,
        },
        {
            "latitude": destination.latitude,
            "longitude": destination.longitude,
        },
    ]

    return {
        "route": route,
        "distance_km": round(
            distance_km,
            2,
        ),
        "duration_minutes": max(
            5,
            int(distance_km * 2.8),
        ),
        "traffic_score": 0.32,
        "hazard_score": 0.12,
    }