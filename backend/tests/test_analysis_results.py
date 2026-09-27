import json
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.government_auth import create_government_token
from app.api.routes import analysis_results as api


def test_results_persist_on_disk_and_require_government_auth(tmp_path):
    folder = tmp_path / "extended_suite_reviewed"
    folder.mkdir()
    (folder / "summary.json").write_text(
        json.dumps(
            {
                "frames_processed": 240,
                "tasks": ["pothole"],
                "output": {"duration_seconds": 10},
            }
        )
    )
    (folder / "annotated.mp4").write_bytes(b"0123456789")
    (folder / "preview.jpg").write_bytes(b"preview")
    # An interrupted run must not appear.
    pending = tmp_path / "incomplete"
    pending.mkdir()
    (pending / "annotated.mp4").write_bytes(b"incomplete")
    client = TestClient(app)
    headers = {"Authorization": "Bearer " + create_government_token()}
    with patch.object(api, "OUTPUTS_ROOT", tmp_path):
        assert client.get("/api/v1/government/analysis-results").status_code == 401
        response = client.get("/api/v1/government/analysis-results", headers=headers)
        assert response.status_code == 200
        videos = response.json()["videos"]
        assert len(videos) == 1
        item = videos[0]
        assert item["recommended"] and item["frames_processed"] == 240
        url = "/api/v1" + item["video_url"]
        assert client.get(url).status_code == 401
        assert client.get(url, headers=headers).content == b"0123456789"
        partial = client.get(url, headers={**headers, "Range": "bytes=0-3"})
        assert partial.status_code == 206 and partial.content == b"0123"
        assert (
            client.get(
                "/api/v1/government/analysis-results/media/unknown", headers=headers
            ).status_code
            == 404
        )
        assert "source" not in item
        # Rebuilding the catalog does not depend on an in-memory upload job.
        assert api.catalog()[0]["videos"][0]["id"] == item["id"]
