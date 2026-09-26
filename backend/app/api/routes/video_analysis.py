import os
import subprocess
import sys
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, File, HTTPException, UploadFile
from fastapi.responses import FileResponse


router = APIRouter(prefix="/video-analysis", tags=["video-analysis"])
ROOT = Path(__file__).resolve().parents[4]
JOBS_ROOT = ROOT / "edge_ai" / "outputs" / "video_analysis"
jobs = {}


def process_video(job_id, source, output):
    jobs[job_id]["status"] = "processing"
    try:
        if not os.environ.get("ROBOFLOW_API_KEY"):
            raise RuntimeError("ROBOFLOW_API_KEY is not configured on the backend")
        command = [sys.executable, "-m", "edge_ai.models.motorcycle_helmet.detect",
                   "--source", str(source), "--output", str(output)]
        completed = subprocess.run(command, cwd=ROOT, capture_output=True, text=True)
        if completed.returncode:
            details = (completed.stderr or completed.stdout or "Detector exited without an error message").strip()
            raise RuntimeError(details[-4000:])
        jobs[job_id].update({"status": "complete", "video_url": f"/api/v1/video-analysis/{job_id}/video"})
    except Exception as exc:
        jobs[job_id].update({"status": "failed", "error": str(exc)})


@router.post("", status_code=202)
async def upload_video(background_tasks: BackgroundTasks, file: UploadFile = File(...)):
    suffix = Path(file.filename or "video.mp4").suffix.lower()
    if suffix not in {".mp4", ".mov", ".avi", ".mkv"}:
        raise HTTPException(status_code=400, detail="Upload an MP4, MOV, AVI, or MKV video")

    job_id = uuid.uuid4().hex
    source = JOBS_ROOT / "uploads" / f"{job_id}{suffix}"
    output = JOBS_ROOT / job_id
    source.parent.mkdir(parents=True, exist_ok=True)
    with source.open("wb") as handle:
        while chunk := await file.read(1024 * 1024):
            handle.write(chunk)
    await file.close()
    jobs[job_id] = {"id": job_id, "status": "queued", "filename": file.filename}
    background_tasks.add_task(process_video, job_id, source, output)
    return jobs[job_id]


@router.get("/{job_id}")
def get_video_status(job_id: str):
    job = jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Video analysis job not found")
    return job


@router.get("/{job_id}/video")
def get_processed_video(job_id: str):
    job = jobs.get(job_id)
    video = JOBS_ROOT / job_id / "motorcycle_helmet_detected.mp4"
    if not job or job.get("status") != "complete" or not video.is_file():
        raise HTTPException(status_code=404, detail="Processed video is not ready")
    return FileResponse(video, media_type="video/mp4", filename="motorcycle_helmet_detected.mp4")