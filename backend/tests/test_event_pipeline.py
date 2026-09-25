from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db.database import Base, get_db
from app.main import app
from app.models.event import Event

SQLALCHEMY_DATABASE_URL = "sqlite://"
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_event_pipeline_and_deduplication():
    from app.core.config import settings
    assert client.get("/api/v1/government/statistics").status_code == 401
    login = client.post("/api/v1/government/login", json={
        "username": settings.GOVERNMENT_USERNAME,
        "password": settings.GOVERNMENT_PASSWORD,
    })
    assert login.status_code == 200
    client.headers["Authorization"] = "Bearer " + login.json()["access_token"]
    timestamp = datetime.utcnow()

    pothole_payload = {
        "event_type": "pothole",
        "severity": "high",
        "confidence": 0.96,
        "latitude": 13.0101,
        "longitude": 77.5678,
        "timestamp": timestamp.isoformat(),
        "bus_id": 101,
        "camera_id": 202,
        "metadata": {"zone": "central"},
    }

    response = client.post("/api/v1/events", json=pothole_payload)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["success"] is True
    assert body["event_id"] is not None
    assert body["status"] in {"new", "existing"}

    stats = client.get("/api/v1/government/statistics")
    assert stats.status_code == 200, stats.text
    stats_json = stats.json()
    assert stats_json["total_alerts"] >= 1
    assert stats_json["potholes"] >= 1

    alerts = client.get("/api/v1/government/alerts")
    assert alerts.status_code == 200, alerts.text
    alerts_json = alerts.json()
    assert any(item["alert_type"] == "pothole" for item in alerts_json)

    road_issues = client.get("/api/v1/government/road-issues")
    assert road_issues.status_code == 200, road_issues.text
    assert any(item["issue_type"] == "pothole" for item in road_issues.json())

    map_events = client.get("/api/v1/government/map-events")
    assert map_events.status_code == 200, map_events.text
    assert any(item["event_type"] == "pothole" and item["latitude"] == 13.0101 for item in map_events.json())

    duplicate_payload = {
        **pothole_payload,
        "timestamp": (timestamp + timedelta(minutes=2)).isoformat(),
    }
    duplicate_response = client.post("/api/v1/events", json=duplicate_payload)
    assert duplicate_response.status_code == 200, duplicate_response.text
    duplicate_json = duplicate_response.json()
    assert duplicate_json["duplicate"] is True
    assert duplicate_json["event_id"] == body["event_id"]

    db = TestingSessionLocal()
    try:
        events = db.query(Event).filter(Event.event_type == "pothole").all()
        assert len(events) == 1
    finally:
        db.close()
