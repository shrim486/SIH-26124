import json
import subprocess
import sys
import uuid
import re
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from app.core.government_auth import require_government_authority


router = APIRouter(prefix="/video-analysis", tags=["video-analysis"], dependencies=[Depends(require_government_authority)])
ROOT = Path(__file__).resolve().parents[4]
JOBS_ROOT = ROOT / "edge_ai" / "outputs" / "video_analysis"
jobs = {}
PROFILES = {
    "motorcycle": ["helmet", "triple_riding", "number_plate"],
    "road": [
        "pothole",
        "damaged_road",
        "waterlogging",
        "road_divider",
        "zebra_crossing",
        "traffic_sign",
    ],
    "plates": ["number_plate"],
    "accident": ["accident"],
    "traffic": ["congestion"],
    "all": [
        "pothole",
        "damaged_road",
        "waterlogging",
        "road_divider",
        "zebra_crossing",
        "traffic_sign",
        "accident",
        "number_plate",
        "helmet",
        "triple_riding",
    ],
}
PROFILES.update({task: [task] for task in PROFILES["all"]})
PROFILES["helmet"] = ["helmet", "number_plate"]
PROFILES["bottleneck"] = ["congestion", "bottleneck"]


def save_job(job_id):
    folder = JOBS_ROOT / "jobs"
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / f"{job_id}.json"
    temporary = target.with_suffix(".tmp")
    temporary.write_text(json.dumps(jobs[job_id]), encoding="utf-8")
    temporary.replace(target)


def process_video(
    job_id,
    source,
    output,
    profile="motorcycle",
    camera="dashcam",
    road_bottom=1.0,
    zones=None,
):
    jobs[job_id]["status"] = "processing"
    save_job(job_id)
    try:
        command = [
            sys.executable,
            "-m",
            "edge_ai.suite",
            "--source",
            str(source),
            "--output",
            str(output),
            "--camera",
            camera,
            "--road-bottom",
            str(road_bottom),
            "--tasks",
            *PROFILES[profile],
        ]
        if zones:
            zones_path = source.with_suffix(".zones.json")
            zones_path.write_text(json.dumps(zones))
            command.extend(["--zones", str(zones_path)])
        completed = subprocess.run(
            command, cwd=ROOT, capture_output=True, text=True, timeout=7200
        )
        if completed.returncode:
            details = (
                completed.stderr
                or completed.stdout
                or "Detector exited without an error message"
            ).strip()
            raise RuntimeError(details[-4000:])
        if not (output / "annotated.mp4").is_file():
            raise RuntimeError("Detector did not produce an annotated video")
        summary = json.loads((output / "summary.json").read_text())
        previews = subprocess.run(
            [
                sys.executable,
                "-m",
                "edge_ai.processing.export_frames",
                "--run",
                str(output),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=60,
        )
        if previews.returncode:
            jobs[job_id][
                "preview_warning"
            ] = "Video completed; frame preview extraction was unavailable"
        jobs[job_id].update(
            {
                "status": "complete",
                "summary": summary,
                "video_url": f"/api/v1/video-analysis/{job_id}/video",
            }
        )
    except Exception as exc:
        jobs[job_id].update({"status": "failed", "error": str(exc)})
    finally:
        save_job(job_id)


@router.post("", status_code=202)
async def upload_video(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    profile: str = Form("motorcycle"),
    camera: str = Form("dashcam"),
    road_bottom: float = Form(1.0),
    zones: str = Form(""),
):
    if not 0 < road_bottom <= 1:
        raise HTTPException(status_code=400, detail="Road bottom must be in (0, 1]")
    if profile not in PROFILES or camera not in {"dashcam", "fixed", "handheld"}:
        raise HTTPException(
            status_code=400, detail="Unknown detector profile or camera type"
        )
    if profile in {"traffic", "congestion", "bottleneck"} and camera != "fixed":
        raise HTTPException(
            status_code=400,
            detail="Traffic queues require a fixed camera; dashcam ego-motion is not calibrated",
        )
    parsed_zones = None
    if zones:
        try:
            parsed_zones = json.loads(zones)
            if not isinstance(parsed_zones, dict) or not parsed_zones:
                raise ValueError("Zones must be an object")
            for box in parsed_zones.values():
                if (
                    not isinstance(box, list)
                    or len(box) != 4
                    or not (0 <= box[0] < box[2] <= 1 and 0 <= box[1] < box[3] <= 1)
                ):
                    raise ValueError("Invalid zone rectangle")
        except (ValueError, TypeError, IndexError) as exc:
            raise HTTPException(
                400,
                "Zones must map names to normalized [left, top, right, bottom] rectangles",
            ) from exc
    if profile == "bottleneck" and (
        not parsed_zones or not {"upstream", "downstream"} <= parsed_zones.keys()
    ):
        raise HTTPException(
            400,
            "Bottleneck analysis needs upstream and downstream zones in traffic-flow order",
        )
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise HTTPException(
            status_code=400, detail="Upload an MP4, MOV, AVI, or MKV video"
        )

    job_id = uuid.uuid4().hex
    source = JOBS_ROOT / "uploads" / f"{job_id}{suffix}"
    output = JOBS_ROOT / job_id
    source.parent.mkdir(parents=True, exist_ok=True)
    with source.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            handle.write(chunk)
    await file.close()
    if source.stat().st_size == 0:
        source.unlink()
        raise HTTPException(400, "The uploaded video is empty")
    jobs[job_id] = {
        "id": job_id,
        "status": "queued",
        "filename": file.filename,
        "profile": profile,
        "camera": camera,
    }
    save_job(job_id)
    background_tasks.add_task(
        process_video,
        job_id,
        source,
        output,
        profile,
        camera,
        road_bottom=road_bottom,
        zones=parsed_zones,
    )
    return jobs[job_id]


@router.get("/{job_id}")
def get_video_status(job_id: str):
    job = jobs.get(job_id)
    if not job and re.fullmatch(r"[a-f0-9]{32}", job_id):
        saved = JOBS_ROOT / "jobs" / f"{job_id}.json"
        if saved.is_file():
            job = json.loads(saved.read_text(encoding="utf-8"))
            if job["status"] in {"queued", "processing"}:
                job.update(
                    status="failed",
                    error="Analysis was interrupted by a server restart. Upload the video again.",
                )
            jobs[job_id] = job
    if not job:
        raise HTTPException(status_code=404, detail="Video analysis job not found")
    return job


@router.get("/{job_id}/video")
def get_processed_video(job_id: str):
    job = get_video_status(job_id)
    video = JOBS_ROOT / job_id / "annotated.mp4"
    if not job or job.get("status") != "complete" or not video.is_file():
        raise HTTPException(status_code=404, detail="Processed video is not ready")
    return FileResponse(video, media_type="video/mp4", filename="annotated.mp4",
                        headers={'Cache-Control':'private, no-store', 'X-Content-Type-Options':'nosniff'})
