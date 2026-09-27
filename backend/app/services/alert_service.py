"""Shared map alert records; demos stay explicit and OCR stays private."""
import json
from math import isfinite
from datetime import datetime, timezone
from sqlalchemy import or_
from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.event import Event
from app.models.analysis_incident import AnalysisIncident

TYPES = {
    'pothole': 'Pothole', 'waterlogging': 'Waterlogging', 'road_damage': 'Road damage',
    'accident': 'Accident', 'helmet_violation': 'No helmet',
    'traffic_violation': 'Traffic violation', 'triple_riding': 'Possible triple riding',
    'rash_driving': 'Possible rash driving', 'congestion': 'Congestion', 'bottleneck': 'Bottleneck',
}
ALIASES = {'damaged_road': 'road_damage', 'without_helmet': 'helmet_violation',
           'high_vehicle_density': 'congestion', 'traffic_bottleneck': 'bottleneck'}


def metadata(event):
    try:
        value = json.loads(event.event_metadata or '{}')
        return value if isinstance(value, dict) else {}
    except (TypeError, ValueError):
        return {}


def public_metadata(value):
    # Only map presentation fields cross into public responses. New private fields
    # (media paths, image data, OCR, device details) stay private by default.
    allowed = {'location_name', 'location_source', 'time_source', 'is_demo',
               'source', 'evidence_available', 'detected_labels'}
    return {key:item for key,item in value.items() if key in allowed}


def event_alert_type(event):
    if event.event_type == 'helmet':
        return 'helmet_violation' if 'without_helmet' in metadata(event).get('detected_labels', []) else None
    kind = ALIASES.get(event.event_type, event.event_type)
    return kind if kind in TYPES else None


def ensure_event_alert(db, event, allow_other=False):
    kind = event_alert_type(event)
    if kind is None and not allow_other:
        return None
    link = db.query(AlertEvent).filter_by(event_id=event.id).first()
    if link:
        return db.get(Alert, link.alert_id)  # Preserve dismissals on retries.
    details = metadata(event)
    kind = kind or event.event_type
    issue_id = details.get('road_issue_id')
    # Reuse older unlinked road alerts when they already represent this issue.
    alert = None
    if issue_id:
        alert = db.query(Alert).filter_by(issue_id=issue_id).order_by(Alert.id).first()
        if alert and db.query(AlertEvent).filter_by(alert_id=alert.id).first():
            return alert
    if alert is None:
        place = details.get('location_name') or f'{event.latitude:.5f}, {event.longitude:.5f}'
        demo = bool(details.get('is_demo') or event.status == 'demo')
        alert = Alert(alert_type=kind,
                      message=f'{"DEMO: " if demo else ""}{TYPES.get(kind, kind.replace("_", " ").title())} reported near {place}',
                      latitude=event.latitude, longitude=event.longitude,
                      severity=event.severity if event.severity in {'low', 'medium', 'high', 'critical'} else 'high' if kind == 'accident' else 'medium',
                      issue_id=issue_id, created_at=event.timestamp or datetime.utcnow(),
                      expires_at=datetime.utcnow() if event.status in {'resolved', 'closed'} else None)
        db.add(alert)
        db.flush()
    db.add(AlertEvent(event_id=event.id, alert_id=alert.id))
    return alert


def iso(value):
    return value.replace(tzinfo=timezone.utc).isoformat() if value else None


def list_alerts(db, *, private=False, active_only=False, include_demo=True):
    query = db.query(Alert, Event, AnalysisIncident).outerjoin(
        AlertEvent, AlertEvent.alert_id == Alert.id).outerjoin(
        Event, Event.id == AlertEvent.event_id).outerjoin(
        AnalysisIncident, AnalysisIncident.event_id == Event.id)
    if active_only:
        query = query.filter(or_(Alert.expires_at.is_(None), Alert.expires_at > datetime.utcnow()))
    result = []
    for alert, event, evidence in query.order_by(Alert.created_at.desc()).limit(500).all():
        details = metadata(event) if event else {}
        demo = bool(details.get('is_demo') or (event and event.status == 'demo'))
        if demo and not include_demo:
            continue
        item = {key: getattr(alert, key) for key in ('id', 'alert_type', 'message', 'latitude', 'longitude', 'severity', 'issue_id')}
        item.update(event_id=event.id if event else None, created_at=iso(alert.created_at),
                    confidence=event.confidence if event else None,
                    issue_status=event.status if event and event.status in {'open', 'in_progress', 'resolved', 'closed'} else 'open',
                    expires_at=iso(alert.expires_at), is_demo=demo,
                    active=alert.expires_at is None or alert.expires_at > datetime.utcnow(),
                    location_name=details.get('location_name', ''),
                    location_source='simulated' if demo else details.get('location_source', 'supplied_coordinates'),
                    time_source='simulated' if demo else details.get('time_source', 'reported_time'),
                    evidence_available=evidence is not None,
                    detected_labels=details.get('detected_labels', []))
        if private:
            item['bus_id'] = event.bus_id if event else None
            item['camera_id'] = event.camera_id if event else None
            item['plate_matches'] = details.get('helmet_plate_matches', [])
            item['reported_registration'] = event.registration_number if event else None
        result.append(item)
    return result


def records_payload(db, *, private=False, archive=False):
    """One alert identity drives both portal maps, counters and recorded lists."""
    rows = {row['id']: row for row in list_alerts(db, private=private)
            if row['alert_type'] in TYPES}
    records = []
    for row in rows.values():
        active = row['active'] and row['issue_status'] not in {'resolved', 'closed'}
        if active == archive:
            continue
        mapped = all(isinstance(row[key], (int, float)) and isfinite(row[key])
                     for key in ('latitude', 'longitude'))
        mapped = mapped and abs(row['latitude']) <= 90 and abs(row['longitude']) <= 180
        records.append(dict(row, active=active, has_location=mapped,
                            reference=f"INC-{row['event_id']:05d}" if row['event_id'] else f"ALT-{row['id']:05d}"))
    return dict(records=records, total=len(records), mapped=sum(row['has_location'] for row in records),
                missing_location=sum(not row['has_location'] for row in records),
                with_evidence=sum(row['evidence_available'] for row in records), archive=archive,
                updated_at=iso(datetime.utcnow()))
