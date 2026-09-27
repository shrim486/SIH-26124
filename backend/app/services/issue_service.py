"""Government case workflow over the same events used by citizen maps."""
import json
from datetime import datetime
from fastapi import HTTPException
from app.models.event import Event
from app.models.road_issue import RoadIssue
from app.models.violation import Violation
from app.models.alert import Alert
from app.models.alert_event import AlertEvent
from app.models.analysis_incident import AnalysisIncident
from app.models.issue_action import IssueAction
from app.services.alert_service import metadata, event_alert_type, ensure_event_alert, iso

STATUSES = {'open', 'in_progress', 'resolved', 'closed'}
FINISHED = {'resolved', 'closed'}
ROAD = {'pothole', 'waterlogging', 'road_damage'}
VIOLATIONS = {'helmet_violation', 'traffic_violation', 'triple_riding', 'rash_driving'}


def issue_status(event):
    return event.status if event.status in STATUSES else 'open'


def source_buses(event):
    reported = metadata(event).get('source_buses', [])
    ids = {value for value in reported if isinstance(value, int) and value > 0} if isinstance(reported, list) else set()
    if event.bus_id is not None:
        ids.add(event.bus_id)
    return sorted(ids)


def category(event):
    kind = event_alert_type(event)
    if kind in ROAD:
        return 'road'
    if kind in VIOLATIONS:
        return 'violations'
    if kind == 'accident':
        return 'accidents'
    if kind in {'congestion', 'bottleneck'}:
        return 'traffic'
    return None


def issue_details(db, event, evidence_ids=None):
    details = metadata(event)
    if evidence_ids is None:
        evidence = db.query(AnalysisIncident).filter_by(event_id=event.id).first() is not None
    else:
        evidence = event.id in evidence_ids
    demo = bool(details.get('is_demo') or event.status == 'demo')
    return dict(id=event.id, event_id=event.id, event_type=event_alert_type(event),
                category=category(event), status=issue_status(event), severity=event.severity,
                latitude=event.latitude, longitude=event.longitude, timestamp=iso(event.timestamp),
                confidence=event.confidence, is_demo=demo, bus_id=event.bus_id, source_bus_ids=source_buses(event), camera_id=event.camera_id,
                location_name=details.get('location_name', ''),
                location_source='simulated' if demo else details.get('location_source', 'supplied_coordinates'),
                evidence_available=evidence, plate_matches=details.get('helmet_plate_matches', []),
                reported_registration=event.registration_number,
                description=details.get('description', ''))


def list_issues(db, group=None, status=None, bus_id=None):
    query = db.query(Event).order_by(Event.timestamp.desc(), Event.id.desc())
    evidence_ids = {row.event_id for row in db.query(AnalysisIncident).all()}
    return [issue_details(db, event, evidence_ids) for event in query.all()
            if category(event) and (bus_id is None or bus_id in source_buses(event)) and (not group or group == category(event))
            and (not status or status == 'all' or issue_status(event) == status)]


def linked_violation(db, event):
    details = metadata(event)
    if details.get('violation_id'):
        return db.get(Violation, details['violation_id'])
    # Older records had no explicit FK. Only accept an exact, unique match.
    if event.event_type not in VIOLATIONS or details.get('is_demo') or event.status == 'demo':
        return None
    rows = db.query(Violation).filter_by(violation_type=event.event_type,
        timestamp=event.timestamp, latitude=event.latitude, longitude=event.longitude,
        registration_number=event.registration_number, bus_id=event.bus_id).all()
    return rows[0] if len(rows) == 1 else None


def update_issue(db, event_id, status, actor, note=''):
    if status not in STATUSES:
        raise HTTPException(422, 'Choose open, in_progress, resolved or closed')
    event = db.get(Event, event_id)
    if not event or not category(event):
        raise HTTPException(404, 'Actionable map issue not found')
    related = [event]
    road_id = metadata(event).get('road_issue_id')
    if road_id:
        road = db.get(RoadIssue, road_id)
        if road:
            road.status = status
            related = [row for row in db.query(Event).all() if metadata(row).get('road_issue_id') == road_id]
    now = datetime.utcnow()
    for row in related:
        previous = issue_status(row)
        details = metadata(row)
        if row.status == 'demo':
            details['is_demo'] = True
        violation = linked_violation(db, row)
        if violation:
            violation.status = {'open': 'pending', 'in_progress': 'reviewed', 'resolved': 'reviewed', 'closed': 'dismissed'}[status]
            details['violation_id'] = violation.id
        row.event_metadata = json.dumps(details)
        row.status = status
        if previous != status:
            db.add(IssueAction(event_id=row.id, previous_status=previous, status=status,
                               actor=actor, note=note, created_at=now))
        alert = ensure_event_alert(db, row)
        if alert and (status in FINISHED or previous in FINISHED):
            alert.expires_at = now if status in FINISHED else None
    if road_id:
        for alert in db.query(Alert).filter_by(issue_id=road_id).all():
            alert.expires_at = now if status in FINISHED else None
    db.commit()
    return issue_details(db, event)


def issue_history(db, event_id):
    event = db.get(Event, event_id)
    if not event or not category(event):
        raise HTTPException(404, 'Actionable map issue not found')
    return [dict(id=row.id, previous_status=row.previous_status, status=row.status,
                 note=row.note, actor=row.actor, created_at=iso(row.created_at))
            for row in db.query(IssueAction).filter_by(event_id=event_id)
            .order_by(IssueAction.created_at.desc(), IssueAction.id.desc()).all()]
