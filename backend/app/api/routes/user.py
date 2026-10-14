from math import radians, sin, cos, sqrt, atan2
import json
from collections import Counter, defaultdict
from functools import lru_cache
from pathlib import Path
from typing import Optional
from datetime import datetime, timezone
from sqlalchemy import or_

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.models.alert import Alert
from app.models.event import Event
from app.models.road_issue import RoadIssue
from app.schemas.journey import JourneyRequest
from app.services.alert_service import list_alerts, metadata, public_metadata


router = APIRouter(
    prefix="/user",
    tags=["Citizen"],
)

ATTACHED_MAP_CLIPS = {
    'bellary-yelahanka-pothole': 'full_project_run_potholes/potholes_detected.mp4',
    'bellary-hebbal-accident': 'bengaluru_accident_demo/annotated.mp4',
    'mekhri-circle-road-damage': 'full_project_run_damaged_road/candidate.mp4',
    'koramangala-ejipura-pothole': 'dashcam_more_sensitive/potholes_detected.mp4',
    'orr-bellandur-congestion': 'demo_traffic/annotated.mp4',
    'orr-marathahalli-congestion': 'demo_highway/annotated.mp4',
    'old-madras-krpuram-waterlogging': 'demo_waterlogging/annotated.mp4',
    'whitefield-hopefarm-road-damage': 'damaged_road_dashcam/candidate.mp4',
}
ATTACHED_CLIPS_ROOT = Path(__file__).resolve().parents[4] / 'edge_ai' / 'outputs'


def _clip_detection_summary(folder):
    """Return compact, reviewable model observations saved with a clip."""
    path = folder / 'detections.jsonl'
    counts = Counter()
    peaks = defaultdict(float)
    moments = []
    if path.is_file():
        try:
            with path.open(encoding='utf-8') as stream:
                for line in stream:
                    row = json.loads(line)
                    detections = row.get('detections') or []
                    labels = []
                    confidence = 0.0
                    for item in detections:
                        label = item.get('label') or item.get('class_name') or item.get('detector')
                        if not label:
                            continue
                        label = str(label).replace('_', ' ')
                        counts[label] += 1
                        labels.append(label)
                        score = item.get('confidence')
                        if isinstance(score, (int, float)):
                            peaks[label] = max(peaks[label], float(score))
                            confidence = max(confidence, float(score))
                    traffic = row.get('traffic') or {}
                    zones = traffic.get('zones') or {}
                    traffic_labels = [str(name).replace('_', ' ') for name, zone in zones.items()
                                      if isinstance(zone, dict) and zone.get('congestion_candidate')]
                    if traffic.get('bottleneck_candidate'):
                        traffic_labels.append('bottleneck candidate')
                    for label in traffic_labels:
                        counts[label] += 1
                        labels.append(label)
                    if labels:
                        moments.append({
                            'time_seconds': round(float(row.get('timestamp_seconds') or 0), 2),
                            'candidate_count': len(labels),
                            'labels': sorted(set(labels)),
                            'peak_confidence': round(confidence, 3) if confidence else None,
                        })
        except (OSError, ValueError, TypeError):
            counts.clear()
            moments = []
    moments.sort(key=lambda item: (item['candidate_count'], item['peak_confidence'] or 0), reverse=True)
    return {
        'candidate_observations': sum(counts.values()),
        'findings': [
            {'label': label, 'observations': count, 'peak_confidence': round(peaks[label], 3) or None}
            for label, count in counts.most_common(8)
        ],
        'moments': moments[:6],
    }


@lru_cache(maxsize=1)
def _attached_clip_catalog():
    clips = []
    for video_id, relative_path in ATTACHED_MAP_CLIPS.items():
        video_path = (ATTACHED_CLIPS_ROOT / relative_path).resolve()
        if not video_path.is_relative_to(ATTACHED_CLIPS_ROOT.resolve()) or not video_path.is_file():
            continue
        folder = video_path.parent
        try:
            summary = json.loads((folder / 'summary.json').read_text(encoding='utf-8'))
        except (OSError, ValueError):
            summary = {}
        source_info = summary.get('source_info') or {}
        input_info = summary.get('output') or summary.get('input') or {}
        images = sorted({
            path.name for pattern in ('preview*.jpg', 'frame_*.jpg', 'preview*.png')
            for path in folder.glob(pattern) if path.is_file()
        })[:8]
        clips.append({
            'video_id': video_id,
            'video_url': f'/user/map-clips/{video_id}/video',
            'title': video_id.replace('-', ' ').replace('_', ' ').title(),
            'source_name': source_info.get('name') or Path(str(summary.get('source') or '').replace('\\', '/')).name or folder.name,
            'source_url': source_info.get('url'),
            'original_location': source_info.get('original_location') or 'Unknown',
            'recorded_at': source_info.get('recorded_at'),
            'location_note': source_info.get('location_note') or 'This clip is attached to a map point for browsing; recording coordinates and time have not been verified.',
            'publisher_page': source_info.get('publisher_page'),
            'tasks': summary.get('tasks') or [],
            'camera': summary.get('camera') or 'unknown',
            'duration_seconds': input_info.get('duration_seconds'),
            'frames_processed': summary.get('frames_processed'),
            'boxes_across_frames': summary.get('boxes_across_frames'),
            'limitations': summary.get('limitations') or 'No detector summary was saved with this clip. Review the footage directly; no incident is verified from this video alone.',
            'findings': _clip_detection_summary(folder),
            'images': [
                {'name': name, 'url': f'/user/map-clips/{video_id}/images/{name}'}
                for name in images
            ],
        })
    return clips


@router.get('/map-clips')
def list_map_clips():
    """Browse the attached road videos and their saved model observations."""
    return {'clips': _attached_clip_catalog()}


@router.get('/map-clips/{video_id}/images/{filename}')
def map_clip_image(video_id: str, filename: str):
    relative_path = ATTACHED_MAP_CLIPS.get(video_id)
    if relative_path is None or Path(filename).name != filename:
        raise HTTPException(404, 'Image not found')
    folder = (ATTACHED_CLIPS_ROOT / relative_path).resolve().parent
    path = (folder / filename).resolve()
    if not path.is_relative_to(ATTACHED_CLIPS_ROOT.resolve()) or not path.is_file() or path.suffix.lower() not in {'.jpg', '.jpeg', '.png'}:
        raise HTTPException(404, 'Image is unavailable')
    media_type = 'image/png' if path.suffix.lower() == '.png' else 'image/jpeg'
    return FileResponse(path, media_type=media_type, headers={'Cache-Control': 'public, max-age=3600', 'Accept-Ranges': 'bytes'})


@router.get('/map-clips/{video_id}/video')
def map_clip_video(video_id: str):
    relative_path = ATTACHED_MAP_CLIPS.get(video_id)
    if relative_path is None:
        raise HTTPException(404, 'Clip not found')
    path = (ATTACHED_CLIPS_ROOT / relative_path).resolve()
    if not path.is_relative_to(ATTACHED_CLIPS_ROOT.resolve()) or not path.is_file() or path.suffix.lower() != '.mp4':
        raise HTTPException(404, 'Clip is unavailable')
    return FileResponse(path, media_type='video/mp4', headers={'Cache-Control': 'public, max-age=3600', 'Accept-Ranges': 'bytes'})


# ============================================================
# MODELS
# ============================================================


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

    active_alerts = list_alerts(db, active_only=True)
    total_alerts = len(active_alerts)

    from app.services.issue_service import list_issues
    issues = list_issues(db)
    open_issues = sum(item['status'] in {'open', 'in_progress'} for item in issues)
    resolved_issues = sum(item['status'] in {'resolved', 'closed'} for item in issues)

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

    recent_alerts = active_alerts[:20]

    return {
        "statistics": {
            "total_alerts": total_alerts,
            "demo_alerts": sum(item['is_demo'] for item in active_alerts),
            "real_alerts": sum(not item['is_demo'] for item in active_alerts),
            "open_issues": open_issues,
            "resolved_issues": resolved_issues,
            "demo_issues": sum(item['is_demo'] for item in issues),
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
            "timestamp": event.timestamp.replace(tzinfo=timezone.utc) if event.timestamp else None,
            "severity": event.severity,
            "status": event.status,
            "is_demo": bool(metadata(event).get('is_demo') or event.status == 'demo'),
            "event_metadata": json.dumps(public_metadata(metadata(event))),
        }
        for event in events
    ]


# ============================================================
# CITIZEN ALERTS
# ============================================================

@router.get('/records')
def recorded_alerts(archive: bool = False, db: Session = Depends(get_db)):
    from app.services.alert_service import records_payload
    return records_payload(db, archive=archive)

@router.get("/alerts")
def get_user_alerts(
    include_demo: bool = True,
    db: Session = Depends(get_db),
):
    return list_alerts(db, active_only=True, include_demo=include_demo)


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
    include_demo: bool = False,
    db: Session = Depends(get_db),
):

    results = []

    # --------------------------------------------------------
    # ROAD ISSUES
    # --------------------------------------------------------

    active_alerts = list_alerts(db, active_only=True, include_demo=include_demo)
    linked_issues = {item['issue_id'] for item in active_alerts if item['issue_id']}
    for issue in db.query(RoadIssue).filter(RoadIssue.status.in_(['open', 'in_progress'])).all():

        if issue.id in linked_issues:
            continue

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

    for alert in active_alerts:

        if alert['latitude'] is None or alert['longitude'] is None:
            continue

        distance = haversine_km(
            latitude,
            longitude,
            alert['latitude'],
            alert['longitude'],
        )

        if distance <= radius_km:

            results.append(
                {
                    **alert,
                    "type": alert['alert_type'],
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

@router.get("/places")
def find_places(q: str = Query(..., min_length=3, max_length=160)):
    from app.services.map_provider import search_places
    return search_places(q)


@router.post("/route", status_code=status.HTTP_200_OK)
def create_user_route(payload: JourneyRequest, db: Session = Depends(get_db)):
    from app.services.journey_service import plan_journey
    return plan_journey(db, payload)


# ============================================================
# CITIZEN REPORTS
# ============================================================

class CitizenReportRequest(BaseModel):
    event_type: str
    latitude: float = Field(..., ge=-90, le=90)
    longitude: float = Field(..., ge=-180, le=180)
    severity: str = "medium"
    description: Optional[str] = None


@router.post("/reports", status_code=status.HTTP_200_OK)
def create_citizen_report(
    report: CitizenReportRequest,
    db: Session = Depends(get_db),
):
    from app.schemas.event import EventCreate
    from app.services.event_service import create_event

    data = EventCreate(
        event_type=report.event_type,
        latitude=report.latitude,
        longitude=report.longitude,
        severity=report.severity,
        metadata={
            "description": report.description,
            "source": "citizen_report",
        }
        if report.description
        else {"source": "citizen_report"},
    )
    result = create_event(db, data)
    return {
        "success": True,
        "message": "Report submitted successfully",
        "event_id": (
            result["event"].id
            if result and "event" in result
            else None
        ),
    }


@router.get("/reports")
def get_citizen_reports(
    db: Session = Depends(get_db),
):
    reports = (
        db.query(Event)
        .filter(Event.event_metadata.contains('citizen_report'))
        .order_by(Event.timestamp.desc())
        .limit(50)
        .all()
    )
    return [
        {
            "id": r.id,
            "event_type": r.event_type,
            "latitude": r.latitude,
            "longitude": r.longitude,
            "severity": r.severity,
            "status": r.status,
            "timestamp": (
                r.timestamp.replace(tzinfo=timezone.utc).isoformat()
                if r.timestamp
                else None
            ),
        }
        for r in reports
    ]
