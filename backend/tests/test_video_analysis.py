import json
from pathlib import Path
from unittest.mock import patch
from fastapi.testclient import TestClient
from app.main import app
from app.core.government_auth import create_government_token
from app.api.routes import video_analysis as api


def test_camera_guard_and_profile_selection(tmp_path):
    with patch.object(api, "JOBS_ROOT", tmp_path), patch.object(
        api, "process_video"
    ) as process:
        client = TestClient(app, headers={"Authorization":"Bearer "+create_government_token()})
        response = client.post(
            "/api/v1/video-analysis",
            files={"file": ("sample.mp4", b"fixture")},
            data={"profile": "traffic", "camera": "dashcam"},
        )
        assert response.status_code == 400
        response = client.post(
            "/api/v1/video-analysis",
            files={"file": ("sample.mp4", b"fixture")},
            data={"profile": "road", "camera": "dashcam"},
        )
        assert response.status_code == 202
        assert process.call_args.args[-2:] == ("road", "dashcam")


def test_offline_command_and_output(tmp_path):
    job = "fixture"
    api.jobs[job] = {"status": "queued"}

    def finished(command, **kwargs):
        from types import SimpleNamespace

        if command[2] == "edge_ai.processing.export_frames":
            return SimpleNamespace(returncode=0)
        assert command[2] == "edge_ai.suite"
        assert "--api-key" not in command
        assert command[-3:] == ["helmet", "triple_riding", "number_plate"]
        (tmp_path / "annotated.mp4").write_bytes(b"fixture")
        (tmp_path / "summary.json").write_text(json.dumps({"frames_processed": 1}))
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0)

    with patch.object(api, "JOBS_ROOT", tmp_path), patch.object(
        api.subprocess, "run", side_effect=finished
    ):
        api.process_video(job, Path("input.mp4"), tmp_path)
    assert api.jobs[job]["status"] == "complete"
    api.jobs.pop(job)
