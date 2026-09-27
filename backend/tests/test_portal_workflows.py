"""API workflows behind report, filter, review, refresh and notification controls."""

from datetime import datetime, timezone
from unittest.mock import patch

from test_accident_evidence import system
from app.api.routes import video_analysis
from app.models.alert import Alert
from app.models.violation import Violation


def test_portal_pages_reports_and_review_actions(system):
    client, headers, sessions, item, folder = system
    for route in ["dashboard", "map-events", "alerts", "reports"]:
        assert client.get("/api/v1/user/" + route).status_code == 200
    for route in [
        "dashboard",
        "statistics",
        "road-issues",
        "violations",
        "accidents",
        "fleet",
        "analytics",
        "map-events",
        "alerts",
        "auth-check",
    ]:
        assert client.get("/api/v1/government/" + route).status_code == 401
        response = client.get("/api/v1/government/" + route, headers=headers)
        assert response.status_code == 200, (route, response.text)
    payload = {
        "event_type": "pothole",
        "latitude": 13.05,
        "longitude": 77.60,
        "description": "Test citizen report",
        "severity": "medium",
    }
    response = client.post("/api/v1/user/reports", json=payload)
    assert response.status_code == 200, response.text
    report_id = response.json()["event_id"]
    reports = client.get("/api/v1/user/reports").json()
    assert reports[0]["id"] == report_id
    assert reports[0]["timestamp"].endswith("+00:00")
    assert (
        client.post(
            "/api/v1/user/reports", json={**payload, "latitude": 91}
        ).status_code
        == 422
    )
    issue = client.get("/api/v1/government/road-issues", headers=headers).json()[0]
    endpoint = f'/api/v1/government/road-issues/{issue["id"]}/status'
    assert client.patch(endpoint, json={"status": "resolved"}).status_code == 401
    assert (
        client.patch(endpoint, headers=headers, json={"status": "nonsense"}).status_code
        == 422
    )
    assert (
        client.patch(endpoint, headers=headers, json={"status": "resolved"}).json()[
            "status"
        ]
        == "resolved"
    )
    assert client.get('/api/v1/user/reports').json()[0]['status'] == 'resolved'
    assert client.get('/api/v1/user/alerts').json() == []
    assert client.get('/api/v1/user/dashboard').json()['statistics']['total_alerts'] == 0
    assert (
        client.get("/api/v1/government/analytics", headers=headers).json()["summary"][
            "resolved_issues"
        ]
        == 1
    )
    with sessions() as db:
        violation = Violation(
            violation_type="helmet_violation",
            latitude=13.01,
            longitude=77.59,
            status="pending",
        )
        alert = Alert(
            alert_type="accident", message="Test alert", latitude=13.02, longitude=77.6
        )
        db.add_all([violation, alert])
        db.commit()
        db.refresh(violation)
        db.refresh(alert)
        violation_id, alert_id = violation.id, alert.id
    endpoint = f"/api/v1/government/violations/{violation_id}/status"
    assert client.patch(endpoint, json={"status": "reviewed"}).status_code == 401
    assert (
        client.patch(endpoint, headers=headers, json={"status": "bad"}).status_code
        == 422
    )
    assert (
        client.patch(endpoint, headers=headers, json={"status": "reviewed"}).json()[
            "status"
        ]
        == "reviewed"
    )
    assert (
        client.get(
            "/api/v1/government/violations?status=pending", headers=headers
        ).json()
        == []
    )
    assert (
        client.get(
            "/api/v1/government/violations?status=reviewed", headers=headers
        ).json()[0]["id"]
        == violation_id
    )
    endpoint = f"/api/v1/government/alerts/{alert_id}"
    assert (
        client.patch(
            endpoint, headers=headers, json={"status": "dismissed"}
        ).status_code
        == 200
    )
    assert alert_id not in [
        alert["id"] for alert in client.get("/api/v1/user/alerts").json()
    ]
    assert (
        client.patch(endpoint, headers=headers, json={"status": "active"}).status_code
        == 200
    )
    assert alert_id in [
        alert["id"] for alert in client.get("/api/v1/user/alerts").json()
    ]


def test_upload_profiles_zones_and_restart_recovery(system, tmp_path):
    client, headers, sessions, item, folder = system
    with patch.object(video_analysis, "JOBS_ROOT", tmp_path), patch.object(
        video_analysis, "process_video"
    ) as process:
        files = {"file": ("sample.mp4", b"fixture")}
        for profile in [
            "pothole",
            "waterlogging",
            "road_divider",
            "zebra_crossing",
            "traffic_sign",
            "helmet",
            "triple_riding",
            "number_plate",
        ]:
            response = client.post(
                "/api/v1/video-analysis", headers=headers, files=files, data={"profile": profile}
            )
            assert response.status_code == 202, response.text
        for zones in [
            "",
            "[]",
            '{"upstream":[0,0,1,1]}',
            '{"upstream":[0,0,2,1],"downstream":[0,0,1,1]}',
        ]:
            response = client.post(
                "/api/v1/video-analysis", headers=headers,
                files=files,
                data={"profile": "bottleneck", "camera": "fixed", "zones": zones},
            )
            assert response.status_code == 400
        response = client.post(
            "/api/v1/video-analysis", headers=headers,
            files=files,
            data={
                "profile": "bottleneck",
                "camera": "fixed",
                "zones": '{"upstream":[0,0,1,0.5],"downstream":[0,0.5,1,1]}',
            },
        )
        assert response.status_code == 202
        identity = response.json()["id"]
        assert process.call_args.kwargs["zones"]["downstream"] == [0, 0.5, 1, 1]
        video_analysis.jobs[identity].update(
            status="complete", summary={"frames_processed": 1}
        )
        video_analysis.save_job(identity)
        video_analysis.jobs.pop(identity)
        assert (
            client.get("/api/v1/video-analysis/" + identity, headers=headers).json()["status"]
            == "complete"
        )
        video_analysis.jobs[identity]["status"] = "processing"
        video_analysis.save_job(identity)
        video_analysis.jobs.pop(identity)
        assert (
            client.get("/api/v1/video-analysis/" + identity, headers=headers).json()["status"]
            == "failed"
        )
        assert (
            client.post(
                "/api/v1/video-analysis", headers=headers, files={"file": ("empty.mp4", b"")}
            ).status_code
            == 400
        )
