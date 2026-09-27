"""Shared filtering and drawing for live inference and saved predictions."""

import cv2


def filter_detections(detections, height, road_bottom=1.0, accident_confidence=0.6):
    if not 0 < road_bottom <= 1:
        raise ValueError("road_bottom must be in (0, 1]")
    result = []
    for detection in detections:
        _, y1, _, y2 = detection["bbox_xyxy"]
        if (y1 + y2) / 2 > height * road_bottom:
            continue
        if (
            detection["label"] == "accident_candidate"
            and detection["confidence"] < accident_confidence
        ):
            continue
        result.append(detection)
    return result


def draw_frame(frame, detections, timestamp, traffic=None):
    annotated = frame.copy()
    text_scale = max(0.45, min(0.8, frame.shape[0] / 1440))
    thickness = max(2, round(frame.shape[0] / 360))
    for detection in detections:
        x1, y1, x2, y2 = map(round, detection["bbox_xyxy"])
        candidate = (
            "candidate" in detection.get("status", "")
            or "candidate" in detection["label"]
        )
        color = (0, 190, 255) if candidate else (40, 220, 90)
        if detection["label"] == "without_helmet":
            color = (60, 60, 245)
        elif detection["label"] == "number_plate":
            color = (255, 210, 40)
        elif detection["label"] in {"motorcycle", "car", "truck", "bus"}:
            color = (190, 180, 170)
        cv2.rectangle(annotated, (x1, y1), (x2, y2), color, thickness)
        label = detection["label"].replace("_", " ")
        if "confidence" in detection:
            label += f" {detection['confidence']:.2f}"
        if detection.get("text"):
            label += " " + detection["text"]
        position = (max(0, x1), max(40, y1 - 5))
        cv2.putText(
            annotated,
            label,
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            text_scale,
            (0, 0, 0),
            3,
            cv2.LINE_AA,
        )
        cv2.putText(
            annotated,
            label,
            position,
            cv2.FONT_HERSHEY_SIMPLEX,
            text_scale,
            color,
            max(1, thickness - 1),
            cv2.LINE_AA,
        )
    banner = f"{timestamp:.2f}s | {len(detections)} boxes | ML candidates"
    if traffic:
        banner += f" | queue:{any(z['congestion_candidate'] for z in traffic['zones'].values())} bottleneck:{traffic['bottleneck_candidate']}"
    cv2.rectangle(annotated, (0, 0), (frame.shape[1], 30), (24, 30, 40), -1)
    cv2.putText(
        annotated, banner, (8, 21), cv2.FONT_HERSHEY_SIMPLEX, 0.48, (255, 255, 255), 1
    )
    return annotated
