"""Integration tests use synthetic frames and explicit prediction fixtures, not model accuracy claims."""

import json
from datetime import datetime, timezone, timedelta
from unittest.mock import patch
import cv2
import numpy as np
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from app.main import app
from app.db.database import Base, get_db
from app.core.government_auth import create_government_token
from app.api.routes import analysis_results as api
from app.models.alert import Alert
from app.models.event import Event
from app.models.analysis_incident import AnalysisIncident


@pytest.fixture
def system(tmp_path):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    sessions = sessionmaker(bind=engine)

    def database():
        with sessions() as db:
            yield db

    previous = app.dependency_overrides.copy()
    app.dependency_overrides[get_db] = database
    folder = tmp_path / "test_accident"
    folder.mkdir()
    writer = cv2.VideoWriter(
        str(folder / "annotated.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), 10, (64, 64)
    )
    rows = []
    for index in range(6):
        frame = np.zeros((64, 64, 3), dtype=np.uint8)
        cv2.rectangle(frame, (10, 10), (40, 40), (0, 255, 0), 2)
        writer.write(frame)
        predictions = (
            [
                {
                    "label": "accident_candidate",
                    "confidence": 0.85,
                    "bbox_xyxy": [10, 10, 40, 40],
                }
            ]
            if index in {1, 2, 3}
            else []
        )
        rows.append(
            {
                "frame_index": index,
                "timestamp_seconds": index / 10,
                "detections": predictions,
            }
        )
    writer.release()
    (folder / "detections.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )
    (folder / "summary.json").write_text(
        json.dumps(
            {
                "frames_processed": 6,
                "tasks": ["accident"],
                "output": {"duration_seconds": 0.6},
            }
        )
    )
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + create_government_token()}
    try:
        with patch.object(api, "OUTPUTS_ROOT", tmp_path):
            item = client.get(
                "/api/v1/government/analysis-results", headers=headers
            ).json()["videos"][0]
            yield client, headers, sessions, item, folder
    finally:
        app.dependency_overrides.clear()
        app.dependency_overrides.update(previous)
        engine.dispose()


def publication(item, demo=True):
    return {
        "segment_id": item["accident_segments"][0]["id"],
        "latitude": 13.018,
        "longitude": 77.594,
        "occurred_at": datetime.now(timezone.utc).isoformat(),
        "location_name": "Demo corridor" if demo else "Reported junction",
        "description": "Integration fixture",
        "demo": demo,
    }


def test_same_incident_on_public_map_and_private_video_with_idempotency(system):
    client, headers, sessions, item, folder = system
    payload = publication(item)
    endpoint = f'/api/v1/government/analysis-results/{item["id"]}/accidents'
    assert client.post(endpoint, json=payload).status_code == 401
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    event_id = response.json()["incident"]["id"]
    public = client.get("/api/v1/user/map-events").json()
    assert len(public) == 1
    assert (
        public[0]["id"] == event_id
        and public[0]["latitude"] == 13.018
        and public[0]["status"] == "demo"
    )
    assert json.loads(public[0]["event_metadata"])["is_demo"] is True
    assert public[0]["timestamp"].endswith("Z") or public[0]["timestamp"].endswith(
        "+00:00"
    )
    accidents = client.get("/api/v1/government/accidents", headers=headers).json()
    assert (
        accidents[0]["id"] == event_id
        and accidents[0]["event_metadata"]["analysis_run_id"] == item["id"]
    )
    assert accidents[0]["timestamp"].endswith("+00:00")
    evidence_url = f"/api/v1/government/analysis-results/incidents/{event_id}"
    assert client.get(evidence_url).status_code == 401
    evidence = client.get(evidence_url, headers=headers).json()
    assert (
        evidence["incident"]["id"] == event_id
        and evidence["video_url"] == item["video_url"]
    )
    assert [frame["time_seconds"] for frame in evidence["frames"]] == [0.1, 0.2, 0.3]
    for frame in evidence["frames"]:
        media = "/api/v1" + frame["image_url"]
        assert client.get(media).status_code == 401
        image = client.get(media, headers=headers)
        assert image.status_code == 200
        assert cv2.imdecode(
            np.frombuffer(image.content, np.uint8), cv2.IMREAD_COLOR
        ).shape == (64, 64, 3)
    assert (
        client.post(endpoint, headers=headers, json=payload).json()["duplicate"] is True
    )
    assert (
        client.post(
            endpoint, headers=headers, json={**payload, "latitude": 12}
        ).status_code
        == 409
    )
    with sessions() as db:
        assert db.query(Event).count() == 1 and db.query(AnalysisIncident).count() == 1
        assert db.query(Alert).count() == 1  # Explicit in-app demo alert, not an emergency dispatch.
    demo_alerts = client.get('/api/v1/user/alerts').json()
    assert demo_alerts[0]['is_demo'] is True
    assert client.get('/api/v1/user/alerts?include_demo=false').json() == []
    assert (
        client.post(
            endpoint, headers=headers, json={**payload, "demo": False}
        ).status_code
        == 409
    )
    saved = client.get("/api/v1/government/analysis-results", headers=headers).json()
    assert "samples" not in saved
    assert saved["videos"][0]["published_incidents"][0]["id"] == event_id


def test_real_report_creates_alert_and_rejects_invalid_publication(system):
    client, headers, sessions, item, folder = system
    payload = publication(item, demo=False)
    endpoint = f'/api/v1/government/analysis-results/{item["id"]}/accidents'
    for bad in [
        {"latitude": 91},
        {"longitude": None},
        {"occurred_at": "2026-01-01T12:00:00"},
        {"occurred_at": (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()},
        {"segment_id": "accident_99999999"},
    ]:
        assert (
            client.post(endpoint, headers=headers, json={**payload, **bad}).status_code
            == 422
        )
    assert client.post(endpoint, headers=headers, json=payload).status_code == 200
    with sessions() as db:
        assert db.query(Alert).count() == 1 and db.query(Event).one().status == "new"


def test_missing_predictions_cannot_create_accident(system):
    client, headers, sessions, item, folder = system
    payload = publication(item)
    (folder / "detections.jsonl").write_text(
        json.dumps({"frame_index": 0, "timestamp_seconds": 0, "detections": []}) + "\n"
    )
    response = client.post(
        f'/api/v1/government/analysis-results/{item["id"]}/accidents',
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422
    with sessions() as db:
        assert db.query(Event).count() == 0


@pytest.mark.parametrize("kind", list(api.MODEL_TYPES))
def test_every_model_type_links_actual_prediction_frames(system, kind):
    client, headers, sessions, item, folder = system
    rows = []
    for index in range(6):
        row = {"frame_index": index, "timestamp_seconds": index / 10, "detections": []}
        if index in {1, 2, 3}:
            if kind in {"congestion", "bottleneck"}:
                row["traffic"] = {
                    "zones": {"upstream": {"congestion_candidate": True}},
                    "bottleneck_candidate": kind == "bottleneck",
                }
            else:
                row["detections"] = [
                    {
                        "label": api.MODEL_TYPES[kind]["labels"][0],
                        "confidence": 0.85,
                        "bbox_xyxy": [10, 10, 40, 40],
                    }
                ]
        rows.append(row)
    (folder / "detections.jsonl").write_text(
        "".join(json.dumps(row) + "\n" for row in rows)
    )
    saved = client.get("/api/v1/government/analysis-results", headers=headers).json()
    segment = next(
        s for s in saved["videos"][0]["detection_segments"] if s["event_type"] == kind
    )
    payload = {**publication(item), "segment_id": segment["id"]}
    endpoint = f'/api/v1/government/analysis-results/{item["id"]}/incidents'
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    event_id = response.json()["incident"]["id"]
    assert response.json()["incident"]["event_type"] == kind
    if kind in {"congestion", "bottleneck"}:
        assert response.json()["incident"]["confidence"] is None
    public = client.get("/api/v1/user/map-events").json()
    assert len(public) == 1 and public[0]["event_type"] == kind
    evidence = client.get(
        f"/api/v1/government/analysis-results/incidents/{event_id}", headers=headers
    ).json()
    assert [frame["time_seconds"] for frame in evidence["frames"]] == [0.1, 0.2, 0.3]
    assert (
        client.post(endpoint, headers=headers, json=payload).json()["duplicate"] is True
    )
    linked = client.get(
        "/api/v1/government/analysis-results/incidents", headers=headers
    ).json()
    assert len(linked) == 1 and linked[0]["id"] == event_id
    assert len(saved["models"]) == 12
    with sessions() as db:
        expected = kind in {'pothole', 'damaged_road', 'waterlogging', 'accident', 'triple_riding', 'congestion', 'bottleneck'}
        assert db.query(Alert).count() == int(expected)
