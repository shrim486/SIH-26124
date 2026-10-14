"""Saved video clips that should be normal, evidence-linked portal alerts."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

ATTACHED_CLIPS_ROOT = Path(__file__).resolve().parents[3] / 'edge_ai' / 'outputs'

ATTACHED_CLIP_RECORDS = [
    {'video_id': 'bellary-yelahanka-pothole', 'alert_type': 'pothole',
     'location_name': 'NH 44 · Bellary Road, Yelahanka', 'latitude': 13.1000, 'longitude': 77.5962,
     'video_file': 'full_project_run_potholes/potholes_detected.mp4'},
    {'video_id': 'bellary-hebbal-accident', 'alert_type': 'accident',
     'location_name': 'NH 44 · Hebbal Flyover', 'latitude': 13.0361, 'longitude': 77.5971,
     'video_file': 'bengaluru_accident_demo/annotated.mp4'},
    {'video_id': 'mekhri-circle-road-damage', 'alert_type': 'road_damage',
     'location_name': 'Bellary Road, Mekhri Circle Flyover', 'latitude': 13.0162, 'longitude': 77.5918,
     'video_file': 'full_project_run_damaged_road/candidate.mp4'},
    {'video_id': 'koramangala-ejipura-pothole', 'alert_type': 'pothole',
     'location_name': '100 Feet Road, Ejipura Flyover', 'latitude': 12.9422, 'longitude': 77.6228,
     'video_file': 'dashcam_more_sensitive/potholes_detected.mp4'},
    {'video_id': 'orr-bellandur-congestion', 'alert_type': 'congestion',
     'location_name': 'Outer Ring Road, Bellandur Flyover', 'latitude': 12.9270, 'longitude': 77.6766,
     'video_file': 'demo_traffic/annotated.mp4'},
    {'video_id': 'orr-marathahalli-congestion', 'alert_type': 'congestion',
     'location_name': 'Outer Ring Road, Marathahalli Bridge', 'latitude': 12.9591, 'longitude': 77.6972,
     'video_file': 'demo_highway/annotated.mp4'},
    {'video_id': 'old-madras-krpuram-waterlogging', 'alert_type': 'waterlogging',
     'location_name': 'Old Madras Road, KR Puram Flyover', 'latitude': 13.0060, 'longitude': 77.6951,
     'video_file': 'demo_waterlogging/annotated.mp4'},
    {'video_id': 'whitefield-hopefarm-road-damage', 'alert_type': 'road_damage',
     'location_name': 'Whitefield Main Road, Hope Farm Flyover', 'latitude': 12.9697, 'longitude': 77.7490,
     'video_file': 'damaged_road_dashcam/candidate.mp4'},
]
ATTACHED_CLIPS_BY_ID = {item['video_id']: item for item in ATTACHED_CLIP_RECORDS}


def clip_video_path(video_id):
    clip = ATTACHED_CLIPS_BY_ID.get(video_id)
    if not clip:
        return None
    root = ATTACHED_CLIPS_ROOT.resolve()
    path = (root / clip['video_file']).resolve()
    return path if path.is_relative_to(root) and path.is_file() and path.suffix.lower() == '.mp4' else None


def clip_summary(video_id):
    video = clip_video_path(video_id)
    if not video:
        return {}
    try:
        summary = json.loads((video.parent / 'summary.json').read_text(encoding='utf-8'))
    except (OSError, ValueError):
        return {}
    return summary if isinstance(summary, dict) else {}


def clip_frame_assets(video_id):
    """Return saved, path-checked frame images without inventing detections."""
    video = clip_video_path(video_id)
    if not video:
        return []

    root = ATTACHED_CLIPS_ROOT.resolve()
    folder = video.parent
    assets = []
    index = folder / 'frames' / 'index.json'
    if index.is_file():
        try:
            rows = json.loads(index.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            rows = []
        for row in rows:
            if not isinstance(row, dict) or not row.get('file'):
                continue
            path = (index.parent / Path(str(row['file'])).name).resolve()
            try:
                time_seconds = max(0.0, float(row.get('time_seconds') or 0))
            except (TypeError, ValueError):
                time_seconds = 0.0
            if (path.is_relative_to(root) and path.is_file()
                    and path.suffix.lower() in {'.jpg', '.jpeg', '.png'}):
                assets.append({'path': path, 'time_seconds': time_seconds})

    if not assets:
        for path in sorted(folder.glob('preview*.jpg')) + sorted(folder.glob('preview*.png')):
            path = path.resolve()
            if path.is_relative_to(root) and path.is_file():
                assets.append({'path': path, 'time_seconds': 0.0})
                break
    return assets[:8]


def ensure_attached_clip_alerts(db):
    """Idempotently place saved clips in the same Event/Alert evidence flow."""
    from app.models.analysis_incident import AnalysisIncident
    from app.models.event import Event
    from app.services.alert_service import ensure_event_alert, metadata

    added = 0
    for clip in ATTACHED_CLIP_RECORDS:
        video = clip_video_path(clip['video_id'])
        if not video:
            continue

        folder_run_id = hashlib.sha256(video.parent.name.encode()).hexdigest()[:24]
        linked = db.query(AnalysisIncident, Event).join(
            Event, Event.id == AnalysisIncident.event_id
        ).filter(AnalysisIncident.run_id == folder_run_id, Event.event_type == clip['alert_type']).first()
        if linked:
            # The starter dataset already has a linked accident and waterlogging
            # record for these exact videos. Reuse those records instead of cloning
            # one source recording into duplicate alerts.
            ensure_event_alert(db, linked[1])
            continue

        source_key = f"attached-map-clip:{clip['video_id']}"
        if db.query(AnalysisIncident).filter_by(source_key=source_key).first():
            continue

        summary = clip_summary(clip['video_id'])
        input_data = summary.get('output') or summary.get('input') or {}
        details = {
            'source': 'video_analysis',
            'attached_map_clip_id': clip['video_id'],
            'location_name': clip['location_name'],
            'description': 'Map location and alert time are assigned for portal display; recording location and recording time are unverified.',
            'evidence_available': True,
            'is_demo': True,
            'location_source': 'simulated',
            'time_source': 'simulated',
            'analysis_run_id': hashlib.sha256(source_key.encode()).hexdigest()[:24],
            'analysis_duration_seconds': input_data.get('duration_seconds'),
            'analysis_frames_processed': summary.get('frames_processed'),
            'analysis_boxes_across_frames': summary.get('boxes_across_frames'),
        }
        event = Event(
            event_type=clip['alert_type'],
            latitude=clip['latitude'],
            longitude=clip['longitude'],
            timestamp=datetime.utcnow(),
            severity='medium',
            status='demo',
            event_metadata=json.dumps(details),
        )
        db.add(event)
        db.flush()
        run_id = details['analysis_run_id']
        segment_id = f"attached_{hashlib.sha256(clip['video_id'].encode()).hexdigest()[:12]}"
        db.add(AnalysisIncident(
            source_key=source_key,
            event_id=event.id,
            run_id=run_id,
            segment_id=segment_id,
        ))
        ensure_event_alert(db, event)
        added += 1

    if added:
        db.commit()
    return added
