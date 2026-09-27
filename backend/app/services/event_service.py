import json
from datetime import datetime, timedelta, timezone

from app.models.alert import Alert
from app.models.event import Event
from app.models.road_issue import RoadIssue
from app.models.violation import Violation
from app.services.alert_service import ensure_event_alert, list_alerts
from app.services.deduplication import (
    calculate_distance,
    find_duplicate_road_issue,
)


# ============================================================
# EVENT CATEGORIES
# ============================================================

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


SEVERITY_ORDER = {
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


VALID_STATUSES = {
    "new",
    "existing",
    "open",
    "in_progress",
    "resolved",
    "closed",
    "pending",
}


# ============================================================
# HELPERS
# ============================================================

def _normalize_event_type(event_type: str) -> str:
    normalized = (
        (event_type or "")
        .strip()
        .lower()
        .replace(" ", "_")
    )
    return {"damaged_road": "road_damage", "without_helmet": "helmet_violation",
            "congestion": "high_vehicle_density", "bottleneck": "traffic_bottleneck"}.get(normalized, normalized)


def _normalize_severity(value: str | None) -> str | None:
    if value is None:
        return None

    normalized = str(value).strip().lower()

    mapping = {
        "urgent": "high",
        "danger": "high",
        "warning": "medium",
        "normal": "low",
    }

    if normalized in SEVERITY_ORDER:
        return normalized

    return mapping.get(normalized, "medium")


def _candidate_severity(
    event_type: str,
    metadata: dict | None = None,
    explicit: str | None = None,
) -> str:

    if explicit:
        normalized = _normalize_severity(explicit)

        if normalized:
            return normalized

    if isinstance(metadata, dict):

        for key in (
            "severity",
            "risk_level",
            "priority",
            "alert_severity",
        ):

            value = metadata.get(key)

            if value:
                normalized = _normalize_severity(str(value))

                if normalized:
                    return normalized

    if event_type in {
        "accident",
        "vulnerable_pedestrian",
    }:
        return "high"

    if event_type in {
        "pothole",
        "road_damage",
        "missing_divider",
        "missing_zebra_crossing",
        "traffic_sign_issue",
    }:
        return "medium"

    if event_type in {
        "traffic_violation",
        "helmet_violation",
        "triple_riding",
        "rash_driving",
        "waterlogging",
        "traffic_bottleneck",
        "high_vehicle_density",
        "pedestrian_risk",
    }:
        return "medium"

    return "low"


def _safe_metadata(value) -> dict:
    """
    Convert incoming metadata into a safe dictionary.
    """

    if value is None:
        return {}

    if isinstance(value, dict):
        return dict(value)

    if isinstance(value, str):

        try:
            parsed = json.loads(value)

            if isinstance(parsed, dict):
                return parsed

        except (json.JSONDecodeError, TypeError):
            pass

    return {}


def _metadata_json(value) -> str | None:
    """
    Convert metadata dictionary to database JSON string.
    """

    metadata = _safe_metadata(value)

    if not metadata:
        return None

    return json.dumps(metadata)


def _severity_max(
    current: str | None,
    incoming: str | None,
) -> str:

    current = _normalize_severity(current) or "low"
    incoming = _normalize_severity(incoming) or "low"

    return max(
        [current, incoming],
        key=lambda value: SEVERITY_ORDER.get(value, 0),
    )


# ============================================================
# DUPLICATE EVENT DETECTION
# ============================================================

def _find_duplicate_event(
    db,
    event_type: str,
    latitude: float,
    longitude: float,
    radius_meters: int = 30,
    time_window_minutes: int = 30,
):

    cutoff = datetime.utcnow() - timedelta(
        minutes=time_window_minutes
    )

    events = (
        db.query(Event)
        .filter(
            Event.event_type == event_type,
            Event.status != "demo",
            Event.timestamp >= cutoff,
        )
        .order_by(Event.timestamp.desc())
        .all()
    )

    for event in events:

        if _safe_metadata(event.event_metadata).get('is_demo') or event.status in {'resolved', 'closed'}:
            continue

        if (
            event.latitude is None
            or event.longitude is None
        ):
            continue

        distance = calculate_distance(
            float(latitude),
            float(longitude),
            float(event.latitude),
            float(event.longitude),
        )

        if distance <= radius_meters:
            return event

    return None


# ============================================================
# CREATE / INGEST EVENT
# ============================================================

def create_event(db, data):

    # A known camera supplies its registered vehicle identity. Legacy external IDs remain accepted.
    if data.camera_id is not None:
        from app.models.camera import Camera
        from fastapi import HTTPException
        camera = db.get(Camera, data.camera_id)
        if camera:
            if data.bus_id is not None and data.bus_id != camera.bus_id:
                raise HTTPException(422, 'The camera is registered to a different bus')
            data = data.model_copy(update={'bus_id': camera.bus_id})

    event_type = _normalize_event_type(
        data.event_type
    )

    timestamp = (
        data.timestamp
        or datetime.utcnow()
    )

    metadata_payload = _safe_metadata(
        data.metadata
    )

    severity = _candidate_severity(
        event_type,
        metadata_payload,
        data.severity,
    )

    # --------------------------------------------------------
    # CATEGORY
    # --------------------------------------------------------

    category = "other"

    if event_type in ROAD_ISSUES:
        category = "road_issue"

    elif event_type in VIOLATIONS:
        category = "violation"

    elif event_type in INCIDENTS:
        category = "incident"

    elif event_type in TRAFFIC_EVENTS:
        category = "traffic"

    # --------------------------------------------------------
    # DUPLICATE EVENT
    # --------------------------------------------------------

    duplicate_event = _find_duplicate_event(
        db=db,
        event_type=event_type,
        latitude=data.latitude,
        longitude=data.longitude,
    ) if category != "violation" and not metadata_payload.get('is_demo') else None

    if duplicate_event is not None:

        if duplicate_event.status not in {'open', 'in_progress'}:
            duplicate_event.status = "existing"

        duplicate_event.confidence = max(
            duplicate_event.confidence or 0.0,
            data.confidence or 0.0,
        )

        duplicate_event.severity = _severity_max(
            duplicate_event.severity,
            severity,
        )

        duplicate_event.timestamp = max(
            duplicate_event.timestamp or timestamp,
            timestamp,
        )

        existing_metadata = _safe_metadata(
            duplicate_event.event_metadata
        )

        existing_metadata["sighting_count"] = (
            existing_metadata.get(
                "sighting_count",
                1,
            )
            + 1
        )

        if data.bus_id is not None:

            source_buses = set(
                existing_metadata.get(
                    "source_buses",
                    [],
                )
            )

            if duplicate_event.bus_id is not None:
                source_buses.add(
                    duplicate_event.bus_id
                )

            source_buses.add(data.bus_id)

            existing_metadata["source_buses"] = sorted(
                source_buses
            )

        # Merge incoming metadata
        existing_metadata.update(
            metadata_payload
        )

        duplicate_event.event_metadata = (
            _metadata_json(existing_metadata)
        )

        ensure_event_alert(db, duplicate_event, allow_other=True)

        db.commit()
        db.refresh(duplicate_event)

        return {
            "event": duplicate_event,
            "category": category,
            "duplicate": True,
            "status": "existing",
        }

    # ========================================================
    # CREATE EVENT
    # ========================================================

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
        event_metadata=_metadata_json(
            metadata_payload
        ),
    )

    db.add(event)
    db.flush()

    if metadata_payload.get('is_demo'):
        event.status = 'demo'
        alert = ensure_event_alert(db, event)
        db.commit()
        db.refresh(event)
        return {'event': event, 'category': category, 'duplicate': False,
                'status': 'demo', 'alert': alert}

    # ========================================================
    # ROAD ISSUE
    # ========================================================

    if event_type in ROAD_ISSUES:

        existing_issue = find_duplicate_road_issue(
            db=db,
            issue_type=event_type,
            latitude=data.latitude,
            longitude=data.longitude,
        )

        if existing_issue is not None:

            existing_issue.last_detected = timestamp

            existing_issue.confidence = max(
                existing_issue.confidence or 0.0,
                data.confidence or 0.0,
            )

            existing_issue.severity = _severity_max(
                existing_issue.severity,
                severity,
            )

            event.status = "existing"
            metadata_payload['road_issue_id'] = existing_issue.id
            event.event_metadata = _metadata_json(metadata_payload)
            ensure_event_alert(db, event, allow_other=True)

            db.commit()

            db.refresh(existing_issue)
            db.refresh(event)

            return {
                "event": event,
                "category": "road_issue",
                "duplicate": True,
                "status": "existing",
                "record": existing_issue,
            }

        # ----------------------------------------------------
        # CREATE ROAD ISSUE
        # ----------------------------------------------------

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
        metadata_payload['road_issue_id'] = issue.id
        event.event_metadata = _metadata_json(metadata_payload)

        # ----------------------------------------------------
        # CREATE ALERT
        # ----------------------------------------------------

        alert = ensure_event_alert(db, event, allow_other=True)

        db.commit()

        db.refresh(event)
        db.refresh(issue)
        db.refresh(alert)

        return {
            "event": event,
            "category": "road_issue",
            "duplicate": False,
            "status": "new",
            "record": issue,
            "alert": alert,
        }

    # ========================================================
    # TRAFFIC VIOLATION
    # ========================================================

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
        db.flush()
        metadata_payload['violation_id'] = violation.id
        event.event_metadata = _metadata_json(metadata_payload)
        ensure_event_alert(db, event)

        db.commit()

        db.refresh(event)
        db.refresh(violation)

        return {
            "event": event,
            "category": "violation",
            "duplicate": False,
            "status": "new",
            "record": violation,
        }

    # ========================================================
    # INCIDENT
    # ========================================================

    if event_type in INCIDENTS:

        alert = ensure_event_alert(db, event, allow_other=True)

        db.commit()

        db.refresh(event)
        db.refresh(alert)

        return {
            "event": event,
            "category": "incident",
            "duplicate": False,
            "status": "new",
            "alert": alert,
        }

    # ========================================================
    # TRAFFIC EVENT
    # ========================================================

    if event_type in TRAFFIC_EVENTS:

        alert = ensure_event_alert(db, event, allow_other=True)

        db.commit()

        db.refresh(event)
        db.refresh(alert)

        return {
            "event": event,
            "category": "traffic",
            "duplicate": False,
            "status": "new",
            "alert": alert,
        }

    # ========================================================
    # OTHER
    # ========================================================

    db.commit()
    db.refresh(event)

    return {
        "event": event,
        "category": "other",
        "duplicate": False,
        "status": "new",
    }


# ============================================================
# GOVERNMENT STATISTICS
# ============================================================

def get_statistics(db):
    from app.services.issue_service import list_issues
    from app.services.alert_service import list_alerts
    issues = list_issues(db)
    active_alerts = list_alerts(db, active_only=True)
    return {
        "total_alerts": len(active_alerts),
        "open_issues": sum(item['status'] in {'open', 'in_progress'} for item in issues),
        "resolved_issues": sum(item['status'] in {'resolved', 'closed'} for item in issues),
        "potholes": sum(item['event_type'] == 'pothole' for item in issues),
        "waterlogging": sum(item['event_type'] == 'waterlogging' for item in issues),
        "accidents": sum(item['event_type'] == 'accident' for item in issues),
        "helmet_violations": sum(item['event_type'] == 'helmet_violation' for item in issues),
        "triple_riding": sum(item['event_type'] == 'triple_riding' for item in issues),
        "traffic_bottlenecks": sum(item['event_type'] == 'bottleneck' for item in issues),
        "demo_issues": sum(item['is_demo'] for item in issues),
        "real_issues": sum(not item['is_demo'] for item in issues),
    }


# ============================================================
# GOVERNMENT MAP EVENTS
# ============================================================

def get_map_events(db):

    events = (
        db.query(Event)
        .order_by(Event.timestamp.desc())
        .limit(500)
        .all()
    )

    result = []

    for event in events:

        metadata = _safe_metadata(
            event.event_metadata
        )

        result.append(
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
                "registration_number": (
                    event.registration_number
                ),
                "severity": event.severity,
                "status": event.status,
                "event_metadata": (
                    metadata or None
                ),
            }
        )

    return result


# ============================================================
# ALERTS
# ============================================================

def get_alerts(db):
    return list_alerts(db, private=True)


# ============================================================
# ROAD ISSUES
# ============================================================

def get_road_issues(db):

    issues = (
        db.query(RoadIssue)
        .order_by(
            RoadIssue.last_detected.desc()
        )
        .limit(500)
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
                issue.first_detected.replace(tzinfo=timezone.utc).isoformat()
                if issue.first_detected
                else None
            ),
            "last_detected": (
                issue.last_detected.replace(tzinfo=timezone.utc).isoformat()
                if issue.last_detected
                else None
            ),
        }
        for issue in issues
    ]


# ============================================================
# ACCIDENTS
# ============================================================

def get_accidents(db):

    accidents = (
        db.query(Event)
        .filter(
            Event.event_type == "accident"
        )
        .order_by(
            Event.timestamp.desc()
        )
        .limit(500)
        .all()
    )

    result = []

    for event in accidents:

        metadata = _safe_metadata(
            event.event_metadata
        )

        result.append(
            {
                "id": event.id,
                "event_type": event.event_type,
                "confidence": event.confidence,
                "latitude": event.latitude,
                "longitude": event.longitude,
                "timestamp": (
                    event.timestamp.replace(tzinfo=timezone.utc).isoformat()
                    if event.timestamp
                    else None
                ),
                "bus_id": event.bus_id,
                "camera_id": event.camera_id,
                "registration_number": (
                    event.registration_number
                ),
                "severity": event.severity,
                "status": event.status,
                "event_metadata": (
                    metadata or None
                ),
            }
        )

    return result


# ============================================================
# FLEET
# ============================================================

def get_fleet(db):
    from app.services.fleet_service import get_fleet as fleet_overview
    return fleet_overview(db)


# ============================================================
# VIOLATIONS
# ============================================================

def get_violations(
    db,
    status: str | None = None,
):

    query = (
        db.query(Violation)
        .order_by(
            Violation.timestamp.desc()
        )
    )

    if status and status != "all":
        query = query.filter(
            Violation.status == status
        )

    violations = query.limit(500).all()

    return [
        {
            "id": violation.id,
            "violation_type": (
                violation.violation_type
            ),
            "registration_number": (
                violation.registration_number
            ),
            "confidence": violation.confidence,
            "latitude": violation.latitude,
            "longitude": violation.longitude,
            "timestamp": (
                violation.timestamp.replace(tzinfo=timezone.utc).isoformat()
                if violation.timestamp
                else None
            ),
            "bus_id": violation.bus_id,
            "status": violation.status,
        }
        for violation in violations
    ]


# ============================================================
# ROAD ISSUE STATUS UPDATE
# ============================================================

def update_road_issue_status(
    db,
    issue_id: int,
    new_status: str,
):

    normalized_status = (
        (new_status or "")
        .strip()
        .lower()
    )

    allowed_issue_statuses = {
        "open",
        "in_progress",
        "resolved",
        "closed",
    }

    if normalized_status not in allowed_issue_statuses:
        return {
            "error": (
                "Invalid status. Allowed values: "
                "open, in_progress, resolved, closed"
            )
        }

    issue = (
        db.query(RoadIssue)
        .filter(
            RoadIssue.id == issue_id
        )
        .first()
    )

    if not issue:
        return None

    from app.services.issue_service import category, update_issue
    linked_events = [event for event in db.query(Event).all()
                     if _safe_metadata(event.event_metadata).get('road_issue_id') == issue.id and category(event)]
    if linked_events:
        update_issue(db, linked_events[0].id, normalized_status, 'government', 'Road issue status update')

    issue.status = normalized_status
    for event in db.query(Event).filter(Event.event_type == issue.issue_type).all():
        if _safe_metadata(event.event_metadata).get('road_issue_id') == issue.id:
            event.status = normalized_status
    for alert in db.query(Alert).filter(Alert.issue_id == issue.id).all():
        alert.expires_at = datetime.utcnow() if normalized_status in {'resolved', 'closed'} else None

    db.commit()
    db.refresh(issue)

    return {
        "id": issue.id,
        "issue_type": issue.issue_type,
        "latitude": issue.latitude,
        "longitude": issue.longitude,
        "confidence": issue.confidence,
        "severity": issue.severity,
        "status": issue.status,
        "first_detected": (
            issue.first_detected.replace(tzinfo=timezone.utc).isoformat()
            if issue.first_detected
            else None
        ),
        "last_detected": (
            issue.last_detected.replace(tzinfo=timezone.utc).isoformat()
            if issue.last_detected
            else None
        ),
    }


# ============================================================
# ANALYTICS
# ============================================================

def get_analytics(db):

    from sqlalchemy import func

    total_events = db.query(Event).count()

    total_road_issues = (
        db.query(RoadIssue).count()
    )

    open_issues = (
        db.query(RoadIssue)
        .filter(
            RoadIssue.status == "open"
        )
        .count()
    )

    in_progress_issues = (
        db.query(RoadIssue)
        .filter(
            RoadIssue.status == "in_progress"
        )
        .count()
    )

    resolved_issues = (
        db.query(RoadIssue)
        .filter(
            RoadIssue.status == "resolved"
        )
        .count()
    )

    total_violations = (
        db.query(Violation).count()
    )

    pending_violations = (
        db.query(Violation)
        .filter(
            Violation.status == "pending"
        )
        .count()
    )

    total_accidents = (
        db.query(Event)
        .filter(
            Event.event_type == "accident"
        )
        .count()
    )

    total_alerts = (
        db.query(Alert).count()
    )

    event_counts = (
        db.query(
            Event.event_type,
            func.count(Event.id),
        )
        .group_by(Event.event_type)
        .all()
    )

    events_by_type = {
        event_type: count
        for event_type, count
        in event_counts
    }

    issue_severities = (
        db.query(
            RoadIssue.severity,
            func.count(RoadIssue.id),
        )
        .group_by(RoadIssue.severity)
        .all()
    )

    issues_by_severity = {
        severity or "unknown": count
        for severity, count
        in issue_severities
    }

    violation_counts = (
        db.query(
            Violation.violation_type,
            func.count(Violation.id),
        )
        .group_by(
            Violation.violation_type
        )
        .all()
    )

    violations_by_type = {
        violation_type: count
        for violation_type, count
        in violation_counts
    }

    fleet_info = get_fleet(db)

    recent_events = (
        db.query(Event)
        .order_by(
            Event.timestamp.desc()
        )
        .limit(10)
        .all()
    )

    return {
        "summary": {
            "total_events": total_events,
            "total_road_issues": (
                total_road_issues
            ),
            "open_issues": open_issues,
            "in_progress_issues": (
                in_progress_issues
            ),
            "resolved_issues": (
                resolved_issues
            ),
            "total_violations": (
                total_violations
            ),
            "pending_violations": (
                pending_violations
            ),
            "total_accidents": (
                total_accidents
            ),
            "total_alerts": total_alerts,
            "total_buses": fleet_info.get(
                "total_buses",
                0,
            ),
            "total_cameras": fleet_info.get(
                "total_cameras",
                0,
            ),
        },

        "events_by_type": events_by_type,

        "issues_by_severity": (
            issues_by_severity
        ),

        "violations_by_type": (
            violations_by_type
        ),

        "fleet": fleet_info,

        "recent_activity": [
            {
                "id": event.id,
                "event_type": event.event_type,
                "severity": event.severity,
                "status": event.status,
                "timestamp": (
                    event.timestamp.isoformat()
                    if event.timestamp
                    else None
                ),
            }
            for event in recent_events
        ],
    }


# ============================================================
# GOVERNMENT DASHBOARD
# ============================================================

def get_dashboard(db):

    statistics = get_statistics(db)
    from app.services.issue_service import list_issues
    events = list_issues(db)
    road_issues = [dict(item, issue_type=item['event_type'], last_detected=item['timestamp'])
                   for item in list_issues(db, group='road')]
    alerts = get_alerts(db)
    accidents = get_accidents(db)
    fleet = get_fleet(db)
    violations = [dict(item, violation_type=item['event_type'], registration_number=item['reported_registration'])
                  for item in list_issues(db, group='violations')]

    return {
        "statistics": statistics,
        "stats": statistics,

        "recent_events": events[:20],
        "events": events,

        "recent_road_issues": (
            road_issues[:20]
        ),
        "road_issues": road_issues,

        "recent_alerts": alerts[:20],
        "alerts": alerts,

        "recent_violations": (
            violations[:20]
        ),
        "violations": violations,

        "accidents": accidents,

        "fleet": fleet,
    }
