"""Government access to completed local analyses and annotated evidence images."""

import hashlib
import json
from datetime import datetime, timezone, timedelta
from pathlib import Path
from functools import lru_cache

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from app.core.government_auth import require_government_authority
from app.db.database import get_db
from app.models.event import Event
from app.models.alert import Alert
from app.models.analysis_incident import AnalysisIncident
from app.services.analysis_evidence import (
    detection_segments,
    extract_evidence,
    MODEL_TYPES,
    prepare_alert_evidence,
)
from app.services.alert_service import ensure_event_alert
from pydantic import BaseModel, Field, AwareDatetime
from sqlalchemy.exc import IntegrityError

OUTPUTS_ROOT = Path(__file__).resolve().parents[4] / "edge_ai/outputs"
router = APIRouter(
    prefix="/government/analysis-results",
    tags=["Government"],
    dependencies=[Depends(require_government_authority)],
)


def catalog():
    root = OUTPUTS_ROOT.resolve()
    media = {}

    def asset(path):
        path = path.resolve()
        if (
            not path.is_relative_to(root)
            or not path.is_file()
            or path.suffix not in {".mp4", ".jpg", ".png", ".jsonl"}
        ):
            return None
        identity = hashlib.sha256(
            path.relative_to(root).as_posix().encode()
        ).hexdigest()[:24]
        media[identity] = path
        return f"/government/analysis-results/media/{identity}"

    videos = []
    summaries = [
        *root.glob("*/summary.json"),
        *root.glob("video_analysis/*/summary.json"),
    ]
    for path in summaries:
        try:
            summary = json.loads(path.read_text(encoding="utf-8"))
            if summary.get("frames_processed", 0) < 1:
                continue
            folder = path.parent
            video = folder / "annotated.mp4"
            if not video.is_file():
                video = folder / "motorcycle_helmet_detected.mp4"
            video_url = asset(video)
            if not video_url:
                continue
            frames = []
            index = folder / "frames/index.json"
            if index.is_file():
                for frame in json.loads(index.read_text()):
                    image_url = asset(folder / "frames" / Path(frame["file"]).name)
                    if image_url:
                        frames.append(
                            {
                                "image_url": image_url,
                                "time_seconds": frame["time_seconds"],
                                "labels": frame.get("labels", []),
                            }
                        )
            incident_frames = {}
            for evidence_index in folder.glob("incidents/*/index.json"):
                segment_frames = []
                for frame in json.loads(evidence_index.read_text()):
                    image_url = asset(evidence_index.parent / Path(frame["file"]).name)
                    if image_url:
                        segment_frames.append(
                            {
                                "image_url": image_url,
                                "time_seconds": frame["time_seconds"],
                                "labels": frame.get("labels", []),
                            }
                        )
                incident_frames[evidence_index.parent.name] = segment_frames
            preview = asset(folder / "preview.jpg")
            segments = detection_segments(folder)
            videos.append(
                {
                    "id": hashlib.sha256(
                        folder.relative_to(root).as_posix().encode()
                    ).hexdigest()[:24],
                    "name": folder.name.replace("_", " "),
                    "recommended": folder.name
                    in {"extended_suite_reviewed", "bengaluru_accident_demo", "demo_slow_riders"},
                    "created_at": datetime.fromtimestamp(
                        path.stat().st_mtime, timezone.utc
                    ).isoformat(),
                    "tasks": summary.get("tasks", ["helmet", "triple_riding"]),
                    "frames_processed": summary["frames_processed"],
                    "duration_seconds": (
                        summary.get("output", {}).get("duration_seconds")
                        if isinstance(summary.get("output"), dict)
                        else None
                    ),
                    "boxes_across_frames": summary.get("boxes_across_frames"),
                    "video_url": video_url,
                    "preview_url": preview,
                    "frames": frames,
                    "accident_segments": [
                        s for s in segments if s["event_type"] == "accident"
                    ],
                    "detection_segments": segments,
                    "camera": summary.get("camera", "unknown"),
                    "source_info": summary.get("source_info"),
                    "incident_frames": incident_frames,
                    "detections_url": asset(folder / "detections.jsonl"),
                }
            )
        except (OSError, ValueError, TypeError, KeyError):
            continue
    videos.sort(key=lambda v: (v["recommended"], v["created_at"]), reverse=True)
    return {"videos": videos}, media


@router.get("")
def list_results(db=Depends(get_db)):
    data = catalog()[0]
    links = db.query(AnalysisIncident).all()
    for video in data["videos"]:
        video["published_incidents"] = [
            {"id": link.event_id, "segment_id": link.segment_id}
            for link in links
            if link.run_id == video["id"]
        ]
    data["models"] = [
        {
            "id": kind,
            "name": kind.replace("_", " ").title(),
            "method": info["method"],
            "videos_analyzed": sum(kind in video["tasks"] for video in data["videos"]),
            "positive_segments": sum(
                s["event_type"] == kind
                for video in data["videos"]
                for s in video["detection_segments"]
            ),
        }
        for kind, info in MODEL_TYPES.items()
    ]
    return data


@router.get("/media/{identity}")
def get_media(identity: str):
    path = catalog()[1].get(identity)
    if path is None:
        raise HTTPException(status_code=404, detail="Analysis asset not found")
    media_type = {
        ".mp4": "video/mp4",
        ".jpg": "image/jpeg",
        ".png": "image/png",
        ".jsonl": "application/x-ndjson",
    }[path.suffix]
    return FileResponse(
        path,
        media_type=media_type,
        filename=path.name,
        headers={"Cache-Control": "private, no-store"},
        content_disposition_type="inline",
    )


class DetectionPublication(BaseModel):
    segment_id: str = Field(pattern=r"^[a-z_]+_\d{8}$", max_length=40)
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    occurred_at: AwareDatetime
    location_name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    demo: bool = False


def resolve_run(run_id):
    data, media = catalog()
    item = next((video for video in data["videos"] if video["id"] == run_id), None)
    if item is None:
        raise HTTPException(404, "Completed video not found")
    return item, media[item["video_url"].rsplit("/", 1)[1]].parent


def event_details(event):
    metadata = json.loads(event.event_metadata or "{}")
    return {
        "id": event.id,
        "event_type": event.event_type,
        "confidence": event.confidence,
        "severity": event.severity,
        "latitude": event.latitude,
        "longitude": event.longitude,
        "timestamp": event.timestamp.replace(tzinfo=timezone.utc).isoformat(),
        "location_name": metadata.get("location_name", ""),
        "description": metadata.get("description", ""),
        "demo": metadata.get("is_demo", False),
        "status": event.status,
    }


@lru_cache(maxsize=64)
def video_fingerprint(path, size, modified):
    digest = hashlib.sha256()
    with open(path, 'rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            digest.update(block)
    return digest.hexdigest()


def evidence_source(item, folder):
    original = (item.get('source_info') or {}).get('url')
    if original:
        return 'url:' + str(original)
    path = folder / 'annotated.mp4'
    if not path.is_file():
        path = folder / 'motorcycle_helmet_detected.mp4'
    stat = path.stat()
    return 'sha256:' + video_fingerprint(str(path), stat.st_size, stat.st_mtime_ns)


@router.post("/{run_id}/incidents")
def publish_detection(run_id: str, payload: DetectionPublication, db=Depends(get_db)):
    item, folder = resolve_run(run_id)
    segment = next(
        (s for s in item["detection_segments"] if s["id"] == payload.segment_id), None
    )
    if segment is None:
        raise HTTPException(
            422,
            "This run has no matching detection meeting the detector threshold",
        )
    occurred = payload.occurred_at.astimezone(timezone.utc)
    if occurred > datetime.now(timezone.utc) + timedelta(minutes=5):
        raise HTTPException(422, "Detection time cannot be in the future")
    occurred = occurred.replace(tzinfo=None)
    key = f"{run_id}:{payload.segment_id}"
    existing = db.query(AnalysisIncident).filter_by(source_key=key).first()
    if existing:
        event = db.get(Event, existing.event_id)
        metadata = json.loads(event.event_metadata or "{}")
        if (
            event.latitude != payload.latitude
            or event.longitude != payload.longitude
            or event.timestamp != occurred
            or metadata.get("is_demo", False) != payload.demo
            or metadata.get("location_name", "") != payload.location_name
            or metadata.get("description", "") != payload.description
        ):
            raise HTTPException(
                409,
                f"This detection is already linked to incident #{event.id}; its details have not been changed",
            )
        return {"incident": event_details(event), "duplicate": True}
    source_key = evidence_source(item, folder)
    if payload.demo:
        # Assigned points cannot multiply the same footage into different cases of one type.
        linked = db.query(AnalysisIncident, Event).join(Event, Event.id == AnalysisIncident.event_id).filter(Event.event_type == segment['event_type']).all()
        for link, previous in linked:
            details = json.loads(previous.event_metadata or '{}')
            if not details.get('is_demo'):
                continue
            previous_source = details.get('evidence_source_key')
            if previous_source is None:
                try:
                    prior_item, prior_folder = resolve_run(link.run_id)
                    previous_source = evidence_source(prior_item, prior_folder)
                except (HTTPException, OSError):
                    previous_source = None
            if link.run_id == run_id or previous_source == source_key:
                raise HTTPException(409, 'This footage is already attached to an assigned incident of this type. Use a different source video for another map location.')
    try:
        alert_details = prepare_alert_evidence(folder, segment)
    except (ValueError, OSError) as exc:
        raise HTTPException(422, str(exc)) from exc
    metadata = {
        **alert_details,
        "source": "video_analysis",
        "analysis_run_id": run_id,
        "evidence_source_key": source_key,
        "segment_id": payload.segment_id,
        "location_name": payload.location_name,
        "description": payload.description,
        "evidence_available": True,
        "is_demo": payload.demo,
        "location_source": "simulated" if payload.demo else "government_supplied",
        "time_source": "simulated" if payload.demo else "government_supplied",
        "method": MODEL_TYPES[segment["event_type"]]["method"],
    }
    event = Event(
        event_type=segment["event_type"],
        confidence=segment["confidence"],
        latitude=payload.latitude,
        longitude=payload.longitude,
        timestamp=occurred,
        severity=(
            "medium"
            if segment["event_type"]
            in {
                "accident",
                "pothole",
                "damaged_road",
                "waterlogging",
                "congestion",
                "bottleneck",
            }
            else "info"
        ),
        status="demo" if payload.demo else "new",
        event_metadata=json.dumps(metadata),
    )
    try:
        db.add(event)
        db.flush()
        db.add(
            AnalysisIncident(
                source_key=key,
                event_id=event.id,
                run_id=run_id,
                segment_id=payload.segment_id,
            )
        )
        ensure_event_alert(db, event)
        db.commit()
        db.refresh(event)
    except IntegrityError as exc:
        db.rollback()
        raise HTTPException(
            409, "This detection was just published; refresh the results"
        ) from exc
    return {"incident": event_details(event), "duplicate": False}


@router.post("/{run_id}/accidents")
def publish_accident(run_id: str, payload: DetectionPublication, db=Depends(get_db)):
    if not payload.segment_id.startswith("accident_"):
        raise HTTPException(422, "Select an accident segment")
    return publish_detection(run_id, payload, db)


@router.get("/incidents")
def list_incidents(db=Depends(get_db)):
    events = (
        db.query(Event)
        .join(AnalysisIncident, AnalysisIncident.event_id == Event.id)
        .order_by(Event.timestamp.desc())
        .all()
    )
    return [event_details(event) for event in events]


@router.get("/incidents/{event_id}")
def incident_evidence(event_id: int, db=Depends(get_db)):
    link = db.query(AnalysisIncident).filter_by(event_id=event_id).first()
    event = db.get(Event, event_id)
    if not link or not event:
        raise HTTPException(404, "No linked detection video for this incident")
    item, _ = resolve_run(link.run_id)
    segment = next(
        (s for s in item["detection_segments"] if s["id"] == link.segment_id), None
    )
    if segment is None:
        raise HTTPException(409, 'The linked detection segment is no longer available. Review this recording before attaching new evidence.')
    item = dict(item)
    item["frames"] = item["incident_frames"].get(link.segment_id, [])
    item["start_seconds"] = segment["start_seconds"] if segment else 0
    item["incident"] = event_details(event)
    item["evidence_segment"] = segment
    return item
