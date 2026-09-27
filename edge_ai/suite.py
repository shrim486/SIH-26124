"""Unified local video analysis with explicit model selection and H.264 output."""

import argparse
from collections import defaultdict, deque
from datetime import datetime
import hashlib
import json
from pathlib import Path
import time

import cv2
import imageio_ffmpeg
from edge_ai.config.config import BASE_DIR, probability, positive_int
from edge_ai.cameras.camera_manager import video_info
from edge_ai.detectors.road_scene import PROMPTS
from edge_ai.processing.annotations import filter_detections, draw_frame

TASKS = [
    "pothole",
    "damaged_road",
    *PROMPTS,
    "accident",
    "number_plate",
    "helmet",
    "triple_riding",
    "congestion",
    "bottleneck",
]


def expand_tasks(tasks):
    selected = list(dict.fromkeys(tasks))
    if 'helmet' in selected and 'number_plate' not in selected:
        selected.append('number_plate')
    return selected


def run(
    source,
    output,
    tasks,
    camera="dashcam",
    zones=None,
    max_frames=None,
    sign_backend="world",
    road_bottom=1.0,
):
    import torch

    torch.set_num_threads(2)
    tasks = expand_tasks(tasks)
    source, output = Path(source).resolve(), Path(output).resolve()
    info = video_info(source)
    if not 0 < road_bottom <= 1:
        raise ValueError("road_bottom must be in (0, 1]")
    if any(t in tasks for t in ("congestion", "bottleneck")) and camera != "fixed":
        raise ValueError(
            "Congestion/bottleneck motion rules need --camera fixed; moving dashcam motion is not calibrated"
        )
    if "bottleneck" in tasks and (
        not zones or not {"upstream", "downstream"} <= zones.keys()
    ):
        raise ValueError(
            "Bottleneck needs upstream/downstream rectangles in --zones JSON, in traffic-flow order"
        )
    if output.exists():
        raise FileExistsError(f"Choose a new output directory: {output}")
    detectors = []
    if "pothole" in tasks:
        from edge_ai.detectors.road_hazards.pothole_detector import RoadDetector

        detectors.append(
            (
                "pothole",
                RoadDetector(BASE_DIR / "models/road_hazards/pothole/best.onnx"),
            )
        )
    if "damaged_road" in tasks:
        from edge_ai.detectors.road_hazards.damaged_road_detector import (
            DamagedRoadDetector,
        )

        detectors.append(
            (
                "damaged_road",
                DamagedRoadDetector(
                    BASE_DIR / "models/road_hazards/damaged_road/best.pt"
                ),
            )
        )
    if "zebra_crossing" in tasks:
        from edge_ai.detectors.zebra_crossing_detector import ZebraCrossingDetector

        detectors.append(("zebra_crossing", ZebraCrossingDetector()))
    if "traffic_sign" in tasks and sign_backend == "supervised":
        from edge_ai.detectors.traffic_sign_detector import TrafficSignDetector

        detectors.append(("traffic_sign", TrafficSignDetector()))
    world_tasks = [
        t
        for t in tasks
        if t in PROMPTS
        and t != "zebra_crossing"
        and not (t == "traffic_sign" and sign_backend == "supervised")
    ]
    if world_tasks:
        from edge_ai.detectors.road_scene import RoadSceneDetector

        detectors.append(("road_scene", RoadSceneDetector(world_tasks)))
    if "accident" in tasks:
        from edge_ai.detectors.accident_detector import AccidentDetector

        detectors.append(("accident", AccidentDetector()))
    if "number_plate" in tasks:
        from edge_ai.detectors.number_plate_detector import NumberPlateDetector

        detectors.append(("number_plate", NumberPlateDetector()))
    traffic_model = person_model = helmet_model = triple = analytics = None
    if any(t in tasks for t in ("helmet", "triple_riding", "congestion", "bottleneck")):
        from ultralytics import YOLO

        traffic_model = YOLO(str(BASE_DIR / "models/motorcycle_helmet/yolo26n.pt"))
    if "helmet" in tasks:
        from edge_ai.models.motorcycle_helmet.offline import OfflineHelmet

        helmet_model = OfflineHelmet(BASE_DIR / "models/motorcycle_helmet/helmet.pt")
    if "triple_riding" in tasks:
        from ultralytics import YOLO
        from edge_ai.models.triple_riding import TripleRidingDetector

        person_model = YOLO(str(BASE_DIR / "models/motorcycle_helmet/yolo26n.pt"))
        triple = TripleRidingDetector()
    if any(t in tasks for t in ("congestion", "bottleneck")):
        from edge_ai.processing.traffic_analytics import TrafficAnalytics

        analytics = TrafficAnalytics(zones=zones)
    output.mkdir(parents=True)
    cap = cv2.VideoCapture(str(source))
    writer = imageio_ffmpeg.write_frames(
        str(output / "annotated.mp4"),
        (info["width"], info["height"]),
        fps=info["fps"],
        pix_fmt_in="bgr24",
        codec="libx264",
        macro_block_size=1,
        output_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        ffmpeg_log_level="error",
    )
    started = time.perf_counter()
    index, total_boxes = 0, 0
    history = defaultdict(lambda: deque(maxlen=5))
    writer.send(None)
    try:
        with (output / "detections.jsonl").open("w", encoding="utf-8") as records:
            while max_frames is None or index < max_frames:
                ok, frame = cap.read()
                if not ok:
                    break
                timestamp = index / info["fps"]
                detections, traffic = [], None
                for name, detector in detectors:
                    results = detector.predict(frame)
                    if name == "damaged_road":
                        result = next(results)
                        results = [
                            {
                                "label": "damaged_road",
                                "model_label": result.names[int(b.cls.item())],
                                "confidence": float(b.conf.item()),
                                "bbox_xyxy": b.xyxy[0].tolist(),
                            }
                            for b in result.boxes
                        ]
                    for detection in results:
                        detection.setdefault("label", name)
                        detection["detector"] = name
                    detections.extend(results)
                if traffic_model:
                    result = traffic_model.track(
                        frame,
                        persist=True,
                        tracker="bytetrack.yaml",
                        classes=[2, 3, 5, 7],
                        conf=0.4,
                        verbose=False,
                    )[0]
                    tracks = []
                    if result.boxes.id is not None:
                        for b in result.boxes:
                            tracks.append(
                                {
                                    "track_id": int(b.id.item()),
                                    "class_id": int(b.cls.item()),
                                    "label": result.names[int(b.cls.item())],
                                    "confidence": float(b.conf.item()),
                                    "bbox_xyxy": b.xyxy[0].tolist(),
                                }
                            )
                    detections.extend(tracks)
                    motorcycles = [
                        (tuple(map(int, t["bbox_xyxy"])), t["track_id"])
                        for t in tracks
                        if t["class_id"] == 3
                    ]
                    if triple:
                        triples = triple.detect(
                            person_model,
                            frame,
                            motorcycles,
                            info["width"],
                            info["height"],
                        )
                        for box, identity in motorcycles:
                            data = triples.get(identity)
                            if data and data["confirmed"]:
                                detections.append(
                                    {
                                        "label": "possible_triple_riding",
                                        "track_id": identity,
                                        "rider_count": data["rider_count"],
                                        "bbox_xyxy": list(box),
                                        "status": "rule_candidate",
                                    }
                                )
                    if helmet_model:
                        from edge_ai.models.motorcycle_helmet.detect import (
                            classify_motorcycle,
                        )

                        for box, identity in motorcycles:
                            data = classify_motorcycle(
                                helmet_model,
                                frame,
                                info["width"],
                                info["height"],
                                box,
                                0.5,
                                history,
                                identity,
                            )
                            if data:
                                detections.append(
                                    {
                                        "label": data["status"] + "_helmet",
                                        "confidence": data["confidence"],
                                        "bbox_xyxy": list(data["box"]),
                                        "track_id": identity,
                                    }
                                )
                    if analytics:
                        traffic = analytics.update(
                            tracks, timestamp, info["width"], info["height"]
                        )
                detections = filter_detections(detections, info["height"], road_bottom)
                annotated = draw_frame(frame, detections, timestamp, traffic)
                writer.send(annotated)
                records.write(
                    json.dumps(
                        {
                            "frame_index": index,
                            "timestamp_seconds": timestamp,
                            "detections": detections,
                            "traffic": traffic,
                        }
                    )
                    + "\n"
                )
                if index == 0:
                    cv2.imwrite(str(output / "preview.jpg"), annotated)
                index += 1
                total_boxes += len(detections)
                if index % 24 == 0:
                    print(f'{index}/{info["frames"]} frames', flush=True)
    finally:
        cap.release()
        writer.close()
    expected = min(info["frames"], max_frames) if max_frames else info["frames"]
    if index != expected:
        raise RuntimeError(f"Decoded {index}/{expected} expected frames")
    summary = {
        "source": str(source),
        "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "tasks": tasks,
        "camera": camera,
        "sign_backend": sign_backend,
        "road_bottom": road_bottom,
        "frames_processed": index,
        "boxes_across_frames": total_boxes,
        "input": info,
        "output": video_info(output / "annotated.mp4"),
        "elapsed_seconds": time.perf_counter() - started,
        "limitations": "Not measured accuracy. Road-scene prompts and accident labels are candidates. Traffic is fixed-camera rules. No audio.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2), flush=True)
    return output


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", required=True)
    p.add_argument(
        "--output",
        default=str(
            BASE_DIR / "outputs" / ("suite_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
        ),
    )
    p.add_argument(
        "--tasks",
        nargs="+",
        choices=TASKS,
        default=[t for t in TASKS if t not in {"congestion", "bottleneck"}],
    )
    p.add_argument("--camera", choices=["dashcam", "fixed", "handheld"], default="dashcam")
    p.add_argument("--zones", type=Path)
    p.add_argument("--max-frames", type=positive_int)
    p.add_argument("--sign-backend", choices=["world", "supervised"], default="world")
    p.add_argument(
        "--road-bottom",
        type=probability,
        default=1.0,
        help="Ignore box centers below this fraction of image height; set for visible dashboard/bonnet",
    )
    a = p.parse_args()
    run(
        a.source,
        a.output,
        a.tasks,
        a.camera,
        json.loads(a.zones.read_text()) if a.zones else None,
        a.max_frames,
        a.sign_backend,
        a.road_bottom,
    )


if __name__ == "__main__":
    main()
