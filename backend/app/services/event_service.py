import json
from datetime import datetime, timedelta

from app.models.alert import Alert
from app.models.event import Event
from app.models.road_issue import RoadIssue
from app.models.violation import Violation
from app.services.deduplication import calculate_distance, find_duplicate_road_issue

ROAD_ISSUES = {
    "pothole",
    "waterlogging",
    "road_damage",
    "missing_divider",
    "missing_zebra_crossing",
    "traffic_sign_issue",
    "other",
}

VIOLATIONS = {
    "traffic_violation",
    "helmet_violation",
    "triple_riding",
    "rash_driving",
}

INCIDENTS = {
    "accident",
    "vulnerable_pedestrian",
}

TRAFFIC_EVENTS = {
    "traffic_bottleneck",
    "high_vehicle_density",
    "pedestrian_risk",
}

SEVERITY_ORDER = {"low": 1, "medium": 2, "high": 3, "critical": 4}


def _normalize_event_type(event_type: str) -> str:
    return (event_type or "").strip().lower().replace(" ", "_")


def _candidate_severity(event_type: str, metadata: dict | None = None, explicit: str | None = None) -> str:
    if explicit:
        normalized = explicit.strip().lower()
        if normalized in SEVERITY_ORDER:
            return normalized
        mapping = {
            "urgent": "high",
            "critical": "critical",
            "danger": "high",
            "warning": "medium",
            "normal": "low",
        }
        return mapping.get(normalized, normalized)

    if isinstance(metadata, dict):
        for key in ("severity", "risk_level", "priority", "alert_severity"):
            value = metadata.get(key)
            if value:
                normalized = str(value).strip().lower()
                if normalized in SEVERITY_ORDER:
                    return normalized
                mapping = {
                    "urgent": "high",
                    "critical": "critical",
                    "danger": "high",
                    "warning": "medium",
                    "normal": "low",
                }
                return mapping.get(normalized, "medium")

    if event_type in {"accident", "vulnerable_pedestrian"}:
        return "high"
    if event_type in {"pothole", "road_damage", "missing_divider", "missing_zebra_crossing", "traffic_sign_issue"}:
        return "medium"
    if event_type in {"traffic_violation", "waterlogging", "traffic_bottleneck"}:
        return "medium"
    return "low"


def _find_duplicate_event(db, event_type: str, latitude: float, longitude: float, radius_meters: int = 30, time_window_minutes: int = 30):
    cutoff = datetime.utcnow() - timedelta(minutes=time_window_minutes)
    events = (
        db.query(Event)
        .filter(Event.event_type == event_type, Event.timestamp >= cutoff)
        .all()
    )
    for event in events:
        if event.latitude is None or event.longitude is None:
            continue
        distance = calculate_distance(float(latitude), float(longitude), float(event.latitude), float(event.longitude))
        if distance <= radius_meters:
            return event
    return None


def create_event(db, data):
    event_type = (data.event_type or "").strip().lower().replace(" ", "_")
    timestamp = data.timestamp or datetime.utcnow()
    metadata_payload = data.metadata if isinstance(data.metadata, dict) else {}
    severity = _candidate_severity(event_type, metadata_payload, data.severity)
    category = "other"

    if event_type in ROAD_ISSUES:
        category = "road_issue"
    elif event_type in VIOLATIONS:
        category = "violation"
    elif event_type in INCIDENTS:
        category = "incident"
    elif event_type in TRAFFIC_EVENTS:
        category = "traffic"

    duplicate_event = _find_duplicate_event(db, event_type, data.latitude, data.longitude)
    if duplicate_event is not None:
        duplicate_event.status = "existing"
        duplicate_event.confidence = max(duplicate_event.confidence or 0.0, data.confidence or 0.0)
        duplicate_event.severity = max(
            [duplicate_event.severity or "low", severity],
            key=lambda value: SEVERITY_ORDER.get(value, 0),
        )
        duplicate_event.timestamp = max(duplicate_event.timestamp or timestamp, timestamp)
        db.commit()
        db.refresh(duplicate_event)
        return {"event": duplicate_event, "category": category, "duplicate": True, "status": "existing"}

    event = Event(
        event_type=event_type,
        confidence=data.confidence,
        latitude=data.latitude,
        longitude=data.longitude,
        timestamp=timestamp,
        bus_id=data.bus_id,
        camera_id=data.camera_id,
        registration_number=data.registration_number,
        severity=severity,
        status="new",
        event_metadata=json.dumps(metadata_payload) if metadata_payload else None,
    )
    db.add(event)
    db.flush()

    if event_type in ROAD_ISSUES:
        existing_issue = find_duplicate_road_issue(
            db=db,
            issue_type=event_type,
            latitude=data.latitude,
            longitude=data.longitude,
        )
        if existing_issue is not None:
            existing_issue.last_detected = timestamp
            existing_issue.confidence = max(existing_issue.confidence or 0.0, data.confidence or 0.0)
            existing_issue.severity = max(
                [existing_issue.severity or "low", severity],
                key=lambda value: SEVERITY_ORDER.get(value, 0),
            )
            db.commit()
            db.refresh(existing_issue)
            db.refresh(event)
            event.status = "existing"
            db.commit()
            return {"event": event, "category": "road_issue", "duplicate": True, "status": "existing"}

        issue = RoadIssue(
            issue_type=event_type,
            latitude=data.latitude,
            longitude=data.longitude,
            confidence=data.confidence,
            severity=severity,
            status="open",
            first_detected=timestamp,
            last_detected=timestamp,
        )
        db.add(issue)
        db.flush()

        alert = Alert(
            alert_type=event_type,
            message=f"{event_type.replace('_', ' ').title()} detected ahead",
            latitude=data.latitude,
            longitude=data.longitude,
            severity=severity,
            issue_id=issue.id,
        )
        db.add(alert)
        db.commit()
        db.refresh(issue)
        db.refresh(event)
        return {"event": event, "category": "road_issue", "duplicate": False, "status": "new", "record": issue, "alert": alert}

    if event_type in VIOLATIONS:
        violation = Violation(
            violation_type=event_type,
            registration_number=data.registration_number,
            confidence=data.confidence,
            latitude=data.latitude,
            longitude=data.longitude,
            timestamp=timestamp,
            bus_id=data.bus_id,
            status="pending",
        )
        db.add(violation)
        db.commit()
        db.refresh(violation)
        db.refresh(event)
        return {"event": event, "category": "violation", "duplicate": False, "status": "new", "record": violation}

    if event_type in INCIDENTS:
        alert = Alert(
            alert_type=event_type,
            message=f"{event_type.replace('_', ' ').title()} detected",
            latitude=data.latitude,
            longitude=data.longitude,
            severity=severity,
        )
        db.add(alert)
        db.commit()
        db.refresh(event)
        db.refresh(alert)
        return {"event": event, "category": "incident", "duplicate": False, "status": "new", "alert": alert}

    if event_type in TRAFFIC_EVENTS:
        alert = Alert(
            alert_type=event_type,
            message=f"{event_type.replace('_', ' ').title()} detected",
            latitude=data.latitude,
            longitude=data.longitude,
            severity=severity,
        )
        db.add(alert)
        db.commit()
        db.refresh(event)
        db.refresh(alert)
        return {"event": event, "category": "traffic", "duplicate": False, "status": "new", "alert": alert}

    db.commit()
    db.refresh(event)
    return {"event": event, "category": "other", "duplicate": False, "status": "new"}
    # ============================================================
# GOVERNMENT DASHBOARD READ FUNCTIONS
# ============================================================

def get_statistics(db):
    total_alerts = db.query(Event).count()

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

    helmet_violations = (
        db.query(Event)
        .filter(Event.event_type == "helmet_violation")
        .count()
    )

    triple_riding = (
        db.query(Event)
        .filter(Event.event_type == "triple_riding")
        .count()
    )

    traffic_bottlenecks = (
        db.query(Event)
        .filter(Event.event_type == "traffic_bottleneck")
        .count()
    )

    return {
        "total_alerts": total_alerts,
        "open_issues": open_issues,
        "resolved_issues": resolved_issues,
        "potholes": potholes,
        "waterlogging": waterlogging,
        "accidents": accidents,
        "helmet_violations": helmet_violations,
        "triple_riding": triple_riding,
        "traffic_bottlenecks": traffic_bottlenecks,
    }


def get_map_events(db):
    """
    Return events required by the government dashboard map.
    """

    events = (
        db.query(Event)
        .order_by(Event.timestamp.desc())
        .all()
    )

    result = []

    for event in events:
        metadata = None

        if event.event_metadata:
            try:
                if isinstance(event.event_metadata, str):
                    metadata = json.loads(event.event_metadata)
                elif isinstance(event.event_metadata, dict):
                    metadata = event.event_metadata
            except (json.JSONDecodeError, TypeError):
                metadata = None

        result.append({
            "id": event.id,
            "event_type": event.event_type,
            "confidence": event.confidence,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "timestamp": (
                event.timestamp.isoformat()
                if event.timestamp
                else None
            ),
            "bus_id": event.bus_id,
            "camera_id": event.camera_id,
            "registration_number": event.registration_number,
            "severity": event.severity,
            "status": event.status,
            "event_metadata": metadata,
        })

    return result


def get_alerts(db):
    alerts = (
        db.query(Alert)
        .order_by(Alert.created_at.desc())
        .all()
    )

    return [
        {
            "id": alert.id,
            "alert_type": alert.alert_type,
            "message": alert.message,
            "latitude": alert.latitude,
            "longitude": alert.longitude,
            "severity": alert.severity,
            "issue_id": alert.issue_id,
            "created_at": (
                alert.created_at.isoformat()
                if alert.created_at
                else None
            ),
            "expires_at": (
                alert.expires_at.isoformat()
                if alert.expires_at
                else None
            ),
        }
        for alert in alerts
    ]


def get_road_issues(db):
    issues = (
        db.query(RoadIssue)
        .order_by(RoadIssue.last_detected.desc())
        .all()
    )

    return [
        {
            "id": issue.id,
            "issue_type": issue.issue_type,
            "latitude": issue.latitude,
            "longitude": issue.longitude,
            "confidence": issue.confidence,
            "severity": issue.severity,
            "status": issue.status,
            "first_detected": (
                issue.first_detected.isoformat()
                if issue.first_detected
                else None
            ),
            "last_detected": (
                issue.last_detected.isoformat()
                if issue.last_detected
                else None
            ),
        }
        for issue in issues
    ]


def get_accidents(db):
    accidents = (
        db.query(Event)
        .filter(Event.event_type == "accident")
        .order_by(Event.timestamp.desc())
        .all()
    )

    return [
        {
            "id": event.id,
            "event_type": event.event_type,
            "confidence": event.confidence,
            "latitude": event.latitude,
            "longitude": event.longitude,
            "timestamp": (
                event.timestamp.isoformat()
                if event.timestamp
                else None
            ),
            "bus_id": event.bus_id,
            "camera_id": event.camera_id,
            "registration_number": event.registration_number,
            "severity": event.severity,
            "status": event.status,
            "event_metadata": (
                json.loads(event.event_metadata)
                if event.event_metadata
                else None
            ),
        }
        for event in accidents
    ]


def get_fleet(db):
    """
    Return fleet information.

    Your current database does not appear to have populated
    Bus/Camera records, so return a safe empty structure.
    """

    try:
        from app.models.bus import Bus
        from app.models.camera import Camera

        buses = db.query(Bus).all()
        cameras = db.query(Camera).all()

        return {
            "total_buses": len(buses),
            "total_cameras": len(cameras),
            "buses": [
                {
                    "id": bus.id,
                    "bus_number": getattr(bus, "bus_number", None),
                    "registration_number": getattr(
                        bus,
                        "registration_number",
                        None,
                    ),
                }
                for bus in buses
            ],
            "cameras": [
                {
                    "id": camera.id,
                    "bus_id": getattr(camera, "bus_id", None),
                    "camera_number": getattr(
                        camera,
                        "camera_number",
                        None,
                    ),
                }
                for camera in cameras
            ],
        }

    except Exception:
        return {
            "total_buses": 0,
            "total_cameras": 0,
            "buses": [],
            "cameras": [],
        }


def get_dashboard(db):
    statistics = get_statistics(db)
    events = get_map_events(db)
    road_issues = get_road_issues(db)
    alerts = get_alerts(db)
    accidents = get_accidents(db)
    fleet = get_fleet(db)

    return {
        "statistics": statistics,
        "stats": statistics,

        "recent_events": events[:20],
        "events": events,

        "recent_road_issues": road_issues[:20],
        "road_issues": road_issues,

        "recent_alerts": alerts[:20],
        "alerts": alerts,

        "recent_violations": [],
        "violations": [],

        "accidents": accidents,

        "fleet": fleet,
    }