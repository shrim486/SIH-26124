"""Render every-frame pothole boxes and save video / JSONL outputs."""
import hashlib
import json
import time
import cv2
import imageio_ffmpeg
import numpy as np
from edge_ai.detectors.road_hazards.pothole_detector import RoadDetector
from edge_ai.cameras.camera_manager import video_info

def annotate(frame, detections, timestamp):
    result = frame.copy()
    label_regions = []
    for box in detections:
        x1, y1, x2, y2 = map(round, box["bbox_xyxy"])
        color = (40, 220, 90) if box["confidence"] >= 0.5 else (0, 190, 255)
        region = result[y1:y2, x1:x2]
        if region.size:
            tint = np.full_like(region, color)
            cv2.addWeighted(region, 0.88, tint, 0.12, 0, dst=region)
        cv2.rectangle(result, (x1, y1), (x2, y2), color, 2)
        label = f"POTHOLE {box['confidence']:.2f}"
        (tw, th), _ = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.48, 1)
        label_x = min(x1, max(0, frame.shape[1] - tw - 10))
        label_y = max(38, y1 - th - 10)
        for _ in range(10):
            rect = (label_x, label_y, label_x + tw + 10, label_y + th + 10)
            if not any(rect[0] < b[2] and rect[2] > b[0] and rect[1] < b[3] and rect[3] > b[1] for b in label_regions):
                break
            label_y += th + 12
        label_regions.append((label_x, label_y, label_x + tw + 10, label_y + th + 10))
        cv2.rectangle(result, (label_x, label_y), (label_x + tw + 10, label_y + th + 10), color, -1)
        cv2.putText(result, label, (label_x + 5, label_y + th + 4), cv2.FONT_HERSHEY_SIMPLEX,
                    0.48, (15, 25, 20), 1, cv2.LINE_AA)
    cv2.rectangle(result, (0, 0), (frame.shape[1], 35), (24, 30, 40), -1)
    cv2.putText(result, f"DASHCAM | {timestamp:05.2f}s | POTHOLE CANDIDATES: {len(detections)} | EVERY FRAME",
                (12, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
    return result


def run(source, weights, output, confidence=0.25, top=0.16, bottom=0.73):
    info = video_info(source)
    detector = RoadDetector(weights, confidence, top, bottom)
    output.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(source))
    writer = imageio_ffmpeg.write_frames(str(output / "potholes_detected.mp4"),
        (info["width"], info["height"]), fps=info["fps"], pix_fmt_in="bgr24",
        codec="libx264", quality=None, macro_block_size=1, ffmpeg_log_level="error",
        output_params=["-crf", "19", "-preset", "fast", "-movflags", "+faststart"])
    writer.send(None)
    index, counts = 0, []
    start = time.perf_counter()
    targets = {round(info["fps"] * second) for second in (1, 3, 5, 8)}
    try:
        with (output / "detections.jsonl").open("w", encoding="utf-8") as handle:
            while True:
                ok, frame = cap.read()
                if not ok:
                    break
                boxes = detector.predict(frame)
                timestamp = index / info["fps"]
                handle.write(json.dumps({"frame_index": index, "timestamp_seconds": timestamp,
                                         "detections": boxes}) + "\n")
                annotated = annotate(frame, boxes, timestamp)
                writer.send(annotated)
                if index in targets:
                    cv2.imwrite(str(output / f"frame_{timestamp:.2f}s.jpg"), annotated)
                counts.append(len(boxes))
                index += 1
                if index % 24 == 0:
                    handle.flush()
                    print(f"{index}/{info['frames']} frames; {sum(counts)} boxes across frames", flush=True)
    finally:
        cap.release()
        writer.close()
    if index != info["frames"]:
        raise RuntimeError("Input video ended before its reported frame count")
    result = video_info(output / "potholes_detected.mp4")
    if result != info:
        raise RuntimeError("Output metadata does not match original video")
    summary = {"source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
               "model": str(weights), "model_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
               "input": info, "output": result, "frames_processed": index,
               "frames_with_candidates": sum(x > 0 for x in counts), "boxes_across_frames": sum(counts),
               "confidence_threshold": confidence, "road_crop_fraction": [top, bottom],
               "method": "Three overlapping road crops; learned ONNX predictions; NMS and containment suppression; every source frame",
               "processing_seconds": time.perf_counter() - start,
               "limitations": "Not a unique pothole count or measured recall. Road region is manually configured for this camera. Misses and false positives remain possible. No audio."}
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
