"""Find actual accident predictions and extract evidence from their annotated video."""

import json
import math
from functools import lru_cache
from pathlib import Path

MODEL_TYPES = {
    "pothole": {"labels": ["pothole"], "method": "ONNX road detector"},
    "damaged_road": {"labels": ["damaged_road"], "method": "RDD road damage detector"},
    "waterlogging": {
        "labels": ["waterlogging"],
        "method": "Experimental open-vocabulary detector",
    },
    "road_divider": {
        "labels": ["road_divider"],
        "method": "Experimental open-vocabulary detector",
    },
    "zebra_crossing": {
        "labels": ["zebra_crossing"],
        "method": "Supervised crosswalk detector",
    },
    "traffic_sign": {
        "labels": ["traffic_sign"],
        "method": "Experimental sign detector",
    },
    "accident": {
        "labels": ["accident", "accident_candidate"],
        "method": "Accident scene candidate detector",
    },
    "number_plate": {"labels": ["number_plate"], "method": "Plate detector and OCR"},
    "helmet": {
        "labels": ["with_helmet", "without_helmet"],
        "method": "Motorcycle and helmet detectors",
    },
    "triple_riding": {
        "labels": ["possible_triple_riding"],
        "method": "Person/motorcycle association and temporal rules",
    },
    "congestion": {"labels": [], "method": "Fixed-camera tracked motion rules"},
    "bottleneck": {
        "labels": [],
        "method": "Fixed-camera upstream/downstream motion rules",
    },
}
LABEL_TYPES = {
    label: kind for kind, info in MODEL_TYPES.items() for label in info["labels"]
}


def accident_segments(folder):
    return [
        segment
        for segment in detection_segments(folder)
        if segment["event_type"] == "accident"
    ]


def detection_segments(folder):
    path = Path(folder) / "detections.jsonl"
    if not path.is_file():
        return []
    stat = path.stat()
    return _segments(str(path), stat.st_mtime_ns, stat.st_size)


@lru_cache(maxsize=16)
def _segments(path, modified, size):
    groups = {}
    try:
        with Path(path).open(encoding="utf-8") as handle:
            previous = -1
            for line in handle:
                row = json.loads(line)
                index = row["frame_index"]
                timestamp = float(row["timestamp_seconds"])
                if (
                    not isinstance(index, int)
                    or index <= previous
                    or not math.isfinite(timestamp)
                    or timestamp < 0
                ):
                    return []
                previous = index
                predictions = {}
                labels = {}
                for detection in row.get("detections", []):
                    kind = LABEL_TYPES.get(detection.get("label"))
                    if not kind:
                        continue
                    confidence = detection.get("confidence")
                    if confidence is not None:
                        confidence = float(confidence)
                        threshold = 0.6 if kind == "accident" else 0.25
                        if (
                            not math.isfinite(confidence)
                            or not threshold <= confidence <= 1
                        ):
                            continue
                    elif kind != "triple_riding":
                        continue
                    predictions.setdefault(kind, []).append(confidence)
                    labels.setdefault(kind, {})[detection["label"]] = max(
                        labels.get(kind, {}).get(detection["label"], 0), confidence or 0
                    )
                traffic = row.get("traffic") or {}
                if any(
                    zone.get("congestion_candidate")
                    for zone in traffic.get("zones", {}).values()
                ):
                    predictions["congestion"] = [None]
                if traffic.get("bottleneck_candidate"):
                    predictions["bottleneck"] = [None]
                for kind, scores in predictions.items():
                    scores = [score for score in scores if score is not None]
                    confidence = max(scores) if scores else None
                    kind_groups = groups.setdefault(kind, [])
                    if (
                        not kind_groups
                        or timestamp - kind_groups[-1]["end_seconds"] > 1.0
                    ):
                        kind_groups.append(
                            {
                                "id": f"{kind}_{index:08d}",
                                "event_type": kind,
                                "start_seconds": timestamp,
                                "end_seconds": timestamp,
                                "confidence": confidence,
                                "detections": [],
                                "label_frame_counts": {},
                                "label_examples": {},
                            }
                        )
                    group = kind_groups[-1]
                    group["end_seconds"] = timestamp
                    if confidence is not None:
                        group["confidence"] = max(group["confidence"] or 0, confidence)
                    group["detections"].append(
                        {"frame_index": index, "time_seconds": timestamp,
                         "labels": sorted(labels.get(kind, {}))}
                    )
                    for label, score in labels.get(kind, {}).items():
                        counts = group["label_frame_counts"]
                        counts[label] = counts.get(label, 0) + 1
                        examples = group["label_examples"]
                        if label not in examples or score > examples[label][0]:
                            examples[label] = (score, len(group["detections"]) - 1)
    except (OSError, ValueError, TypeError, KeyError):
        return []
    result = [group for kind_groups in groups.values() for group in kind_groups]
    for group in result:
        frames = group.pop("detections")
        group["detected_frames"] = len(frames)
        examples = group.pop("label_examples")
        group["detected_labels"] = sorted(examples)
        # Preserve both helmet classes even when one appears only briefly.
        # Other types keep their chronological sample layout.
        chosen = {value[1] for value in examples.values()} if group["event_type"] == "helmet" else set()
        for i in sorted({round(i * (len(frames) - 1) / 4) for i in range(5)}):
            if len(chosen) < 5:
                chosen.add(i)
        group["frames"] = [frames[i] for i in sorted(chosen)]
    return sorted(
        result, key=lambda group: (group["start_seconds"], group["event_type"])
    )


def extract_evidence(folder, segment):
    import cv2

    folder = Path(folder)
    cap = cv2.VideoCapture(str(folder / "annotated.mp4"))
    if not cap.isOpened():
        raise ValueError("Cannot open the annotated evidence video")
    target = folder / "incidents" / segment["id"]
    target.mkdir(parents=True, exist_ok=True)
    index = []
    try:
        for row in segment["frames"]:
            frame_index = row["frame_index"]
            cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Missing annotated frame {frame_index}")
            name = f"frame_{frame_index:08d}.jpg"
            if not cv2.imwrite(str(target / name), frame):
                raise ValueError("Could not save evidence image")
            index.append({"file": name, "time_seconds": row["time_seconds"],
                          "labels": row.get("labels", [])})
    finally:
        cap.release()
    temporary = target / "index.json.tmp"
    temporary.write_text(json.dumps(index, indent=2))
    temporary.replace(target / "index.json")
    return index


def prepare_alert_evidence(folder, segment):
    """Keep no-helmet/plate associations and their actual simultaneous frames."""
    from app.services.helmet_plates import helmet_plate_evidence

    details = {"detected_labels": segment.get("detected_labels", [])}
    frames = {row["frame_index"]: row for row in segment["frames"]}
    if segment["event_type"] == "helmet" and "without_helmet" in details["detected_labels"]:
        matches = helmet_plate_evidence(folder, segment)
        details["helmet_plate_matches"] = matches
        for match in matches:
            frames[match["frame_index"]] = {
                "frame_index": match["frame_index"], "time_seconds": match["time_seconds"],
                "labels": ["without_helmet", "number_plate"],
            }
    extract_evidence(folder, {**segment, "frames": sorted(frames.values(), key=lambda row: row["frame_index"])})
    return details
