"""Detect motorcycles and classify nearby rider heads as helmeted or not."""

import argparse
import json
import os
import shutil
import subprocess
import time
from collections import defaultdict, deque
from getpass import getpass
from pathlib import Path

import cv2
import requests
from roboflow import Roboflow
from ultralytics import YOLO
from edge_ai.models.triple_riding import TripleRidingDetector


DEFAULT_WORKSPACE = "helmet-detection-1prq9"
DEFAULT_PROJECT = "helmet-detection_yolov8-cuaay"
DEFAULT_VERSION = 1
DEFAULT_VEHICLE_WEIGHTS = Path(__file__).with_name("yolo26n.pt")


def parse_probability(value):
    result = float(value)
    if not 0 <= result <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return result


def roboflow_predictions(model, crop, confidence):
    for attempt in range(3):
        try:
            response = model.predict(crop, confidence=round(confidence * 100), overlap=30)
            payload = response.json() if hasattr(response, "json") else response
            return payload.get("predictions", []) if isinstance(payload, dict) else []
        except requests.RequestException as exc:
            if attempt == 2:
                print(f"Helmet API unavailable for crop; continuing video: {exc}", flush=True)
                return []
            time.sleep(2 ** attempt)
    return []


def classify_motorcycle(model, frame, frame_width, frame_height, motorcycle_box, confidence, history, track_id):
    x1, y1, x2, y2 = motorcycle_box
    motorcycle_width = x2 - x1
    motorcycle_height = y2 - y1
    if motorcycle_width <= 0 or motorcycle_height <= 0:
        return None

    crop_x1 = max(0, x1 - int(motorcycle_width * 0.35))
    crop_x2 = min(frame_width, x2 + int(motorcycle_width * 0.35))
    crop_y1 = max(0, y1 - int(motorcycle_height * 1.8))
    crop_y2 = min(frame_height, y2 + int(motorcycle_height * 0.15))
    crop = frame[crop_y1:crop_y2, crop_x1:crop_x2]
    if crop.size == 0:
        return None

    candidates = []
    for prediction in roboflow_predictions(model, crop, confidence):
        label = str(prediction.get("class", "")).lower().replace("-", "_")
        if label not in {"with_helmet", "without_helmet", "with helmet", "without helmet"}:
            continue

        prediction_confidence = float(prediction.get("confidence", 0))
        center_x = float(prediction["x"])
        center_y = float(prediction["y"])
        prediction_width = float(prediction["width"])
        prediction_height = float(prediction["height"])
        head_box = (
            int(center_x - prediction_width / 2) + crop_x1,
            int(center_y - prediction_height / 2) + crop_y1,
            int(center_x + prediction_width / 2) + crop_x1,
            int(center_y + prediction_height / 2) + crop_y1,
        )
        head_center_y = (head_box[1] + head_box[3]) / 2
        motorcycle_center_y = (y1 + y2) / 2
        if head_center_y > motorcycle_center_y or head_center_y < y1 - motorcycle_height * 2.0:
            continue
        candidates.append({"label": label, "confidence": prediction_confidence, "box": head_box})

    if not candidates:
        return None

    best = max(candidates, key=lambda candidate: candidate["confidence"])
    current = "without" if "without" in best["label"] else "with"
    history[track_id].append(current)
    votes = history[track_id]
    if len(votes) < 3:
        return None
    if votes.count("without") >= 2:
        status = "without"
    elif votes.count("with") >= 2:
        status = "with"
    else:
        return None
    return {"status": status, "confidence": best["confidence"], "box": best["box"]}


def run(source, output, api_key, vehicle_weights, workspace, project, version, helmet_confidence):
    source = Path(source).expanduser().resolve()
    output = Path(output).expanduser().resolve()
    vehicle_weights_path = Path(vehicle_weights).expanduser()
    vehicle_weights_source = (str(vehicle_weights_path.resolve())
                              if vehicle_weights_path.is_file() else vehicle_weights_path.name)
    if not source.is_file():
        raise FileNotFoundError(f"Input video not found: {source}")

    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise ValueError(f"Cannot open input video: {source}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT))
    total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    if min(fps, width, height, total_frames) <= 0:
        capture.release()
        raise ValueError(f"Cannot read video metadata: {source}")

    output.mkdir(parents=True, exist_ok=False)
    raw_video = output / "motorcycle_helmet_detected_raw.mp4"
    final_video = output / "motorcycle_helmet_detected.mp4"
    writer = cv2.VideoWriter(str(raw_video),
                             cv2.VideoWriter_fourcc(*"mp4v"), fps, (width, height))
    if not writer.isOpened():
        capture.release()
        raise OSError("Cannot create output video")

    vehicle_model = YOLO(vehicle_weights_source)
    helmet_model = Roboflow(api_key=api_key).workspace(workspace).project(project).version(version).model
    history = defaultdict(lambda: deque(maxlen=5))
    triple_detector = TripleRidingDetector(confidence=0.55)
    records = []
    frame_number = 0
    try:
        while True:
            ok, frame = capture.read()
            if not ok:
                break
            frame_number += 1
            results = vehicle_model.track(frame, persist=True, tracker="bytetrack.yaml",
                                           classes=[3], conf=0.50, verbose=False)
            frame_detections = []
            if results and results[0].boxes is not None:
                boxes = results[0].boxes
                coordinates = boxes.xyxy.cpu().numpy() if boxes.xyxy is not None else []
                track_ids = (boxes.id.cpu().numpy().astype(int).tolist()
                             if boxes.id is not None else list(range(len(coordinates))))
                motorcycle_tracks = [(tuple(map(int, box)), int(track_id))
                                     for box, track_id in zip(coordinates, track_ids)]
                triple_results = triple_detector.detect(
                    vehicle_model, frame, motorcycle_tracks, width, height)
                for box, track_id in zip(coordinates, track_ids):
                    motorcycle_box = tuple(map(int, box))
                    x1, y1, x2, y2 = motorcycle_box
                    track_id = int(track_id)
                    triple = triple_results.get(track_id, {
                        "rider_count": 0, "confirmed": False, "people": []})
                    frame_detection = {
                        "track_id": track_id,
                        "triple_riding": {
                            "confirmed": triple["confirmed"],
                            "rider_count": triple["rider_count"],
                        },
                    }
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (255, 0, 0), 2)
                    cv2.putText(frame, "Motorcycle", (x1, max(25, y1 - 8)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    for person_box in triple["people"]:
                        px1, py1, px2, py2 = person_box
                        cv2.rectangle(frame, (px1, py1), (px2, py2), (255, 255, 0), 2)
                    if triple["confirmed"]:
                        cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 4)
                        cv2.putText(frame, "POSSIBLE TRIPLE RIDING",
                                    (x1, min(height - 10, y2 + 30)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.60, (0, 0, 255), 2)
                    helmet = classify_motorcycle(helmet_model, frame, width, height,
                                                 motorcycle_box, helmet_confidence, history, track_id)
                    if helmet is not None:
                        hx1, hy1, hx2, hy2 = helmet["box"]
                        color = (0, 0, 255) if helmet["status"] == "without" else (0, 255, 0)
                        text = f"{'WITHOUT' if helmet['status'] == 'without' else 'WITH'} HELMET {helmet['confidence']:.2f}"
                        cv2.rectangle(frame, (hx1, hy1), (hx2, hy2), color, 3)
                        cv2.putText(frame, text, (hx1, max(25, hy1 - 8)),
                                    cv2.FONT_HERSHEY_SIMPLEX, 0.55, color, 2)
                        frame_detection.update({"helmet_status": helmet["status"],
                                                "helmet_confidence": helmet["confidence"],
                                                "helmet_bbox_xyxy": [hx1, hy1, hx2, hy2]})
                    frame_detections.append(frame_detection)
            writer.write(frame)
            records.append({"frame_index": frame_number - 1, "timestamp_seconds": (frame_number - 1) / fps,
                            "detections": frame_detections})
            if frame_number % 25 == 0:
                print(f"Processed {frame_number}/{total_frames} frames", flush=True)
    finally:
        capture.release()
        writer.release()

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise RuntimeError("FFmpeg is required to create browser-compatible video output")
    subprocess.run([ffmpeg, "-y", "-nostdin", "-v", "error", "-i", str(raw_video),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-movflags", "+faststart",
                    str(final_video)], check=True)
    raw_video.unlink(missing_ok=True)

    (output / "detections.jsonl").write_text(
        "".join(json.dumps(record) + "\n" for record in records), encoding="utf-8")
    summary = {"source": str(source), "output": str(final_video),
               "frames_processed": frame_number, "fps": fps, "resolution": [width, height],
               "helmet_project": f"{workspace}/{project}/version/{version}",
               "helmet_confidence": helmet_confidence, "audio_retained": False}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Path to the input MP4/video")
    parser.add_argument("--output", default="edge_ai/outputs/motorcycle_helmet")
    parser.add_argument("--api-key", default=os.environ.get("ROBOFLOW_API_KEY"))
    parser.add_argument("--vehicle-weights", default=str(DEFAULT_VEHICLE_WEIGHTS))
    parser.add_argument("--workspace", default=DEFAULT_WORKSPACE)
    parser.add_argument("--project", default=DEFAULT_PROJECT)
    parser.add_argument("--version", type=int, default=DEFAULT_VERSION)
    parser.add_argument("--helmet-confidence", type=parse_probability, default=0.50)
    args = parser.parse_args()
    api_key = args.api_key or getpass("Roboflow API key: ")
    if not api_key:
        parser.error("A Roboflow API key is required")
    run(args.source, args.output, api_key, args.vehicle_weights, args.workspace,
        args.project, args.version, args.helmet_confidence)


if __name__ == "__main__":
    main()