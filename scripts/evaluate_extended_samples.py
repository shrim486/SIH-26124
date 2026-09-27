"""Small labeled development-set checks plus explicitly non-benchmark demo images."""

import json
from pathlib import Path
import sys
import gc
import cv2
import torch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edge_ai.config.config import BASE_DIR


def iou(a, b):
    left, top = max(a[0], b[0]), max(a[1], b[1])
    right, bottom = min(a[2], b[2]), min(a[3], b[3])
    intersection = max(0, right - left) * max(0, bottom - top)
    return intersection / (
        (a[2] - a[0]) * (a[3] - a[1])
        + (b[2] - b[0]) * (b[3] - b[1])
        - intersection
        + 1e-9
    )


def draw(frame, predictions, path):
    frame = frame.copy()
    for p in predictions:
        x1, y1, x2, y2 = map(round, p["bbox_xyxy"])
        cv2.rectangle(frame, (x1, y1), (x2, y2), (40, 220, 90), 2)
        text = p["label"] + " " + str(p.get("text", ""))
        cv2.putText(
            frame,
            text,
            (x1, max(18, y1 - 5)),
            cv2.FONT_HERSHEY_SIMPLEX,
            0.5,
            (40, 220, 90),
            1,
        )
    cv2.imwrite(str(path), frame)


def main():
    torch.set_num_threads(2)
    out = BASE_DIR / "outputs/extended_evaluation"
    out.mkdir(exist_ok=True)
    from edge_ai.detectors.zebra_crossing_detector import ZebraCrossingDetector
    from edge_ai.detectors.road_scene import RoadSceneDetector
    from edge_ai.detectors.traffic_sign_detector import TrafficSignDetector
    from edge_ai.detectors.accident_detector import AccidentDetector
    from edge_ai.detectors.number_plate_detector import NumberPlateDetector
    from edge_ai.models.motorcycle_helmet.offline import OfflineHelmet

    report = {
        "scope": "Small development subsets, not representative accuracy. Public checkpoints may have seen related data. Demo images have no box ground truth."
    }
    for name, dataset, factory in [
        ("zebra_crossing", "zebra_crossing", ZebraCrossingDetector),
        ("traffic_sign", "traffic_sign", lambda: RoadSceneDetector(["traffic_sign"])),
        ("traffic_sign_supervised", "traffic_sign", TrafficSignDetector),
    ]:
        model = factory()
        tp = fp = fn = images = 0
        for path in sorted(
            (BASE_DIR / "dataset" / dataset / "test/images").glob("*.jpg")
        ):
            frame = cv2.imread(str(path))
            h, w = frame.shape[:2]
            predictions = model.predict(frame)
            truth = []
            for line in (
                (path.parent.parent / "labels" / f"{path.stem}.txt")
                .read_text()
                .splitlines()
            ):
                if not line.strip():
                    continue
                cls, x, y, bw, bh = map(float, line.split())
                truth.append(
                    [
                        (x - bw / 2) * w,
                        (y - bh / 2) * h,
                        (x + bw / 2) * w,
                        (y + bh / 2) * h,
                    ]
                )
            unmatched = set(range(len(truth)))
            for prediction in sorted(
                predictions, key=lambda d: d["confidence"], reverse=True
            ):
                best = max(
                    unmatched,
                    key=lambda i: iou(prediction["bbox_xyxy"], truth[i]),
                    default=None,
                )
                if (
                    best is not None
                    and iou(prediction["bbox_xyxy"], truth[best]) >= 0.5
                ):
                    tp += 1
                    unmatched.remove(best)
                else:
                    fp += 1
            fn += len(unmatched)
            images += 1
            draw(frame, predictions, out / f"{name}_{images}.jpg")
        report[name] = {
            "images": images,
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "precision_at_iou50": tp / (tp + fp) if tp + fp else 0,
            "recall_at_iou50": tp / (tp + fn) if tp + fn else 0,
            "not_mAP": True,
        }
        print(name, report[name], flush=True)
        del model
        gc.collect()
        (out / "report.json").write_text(json.dumps(report, indent=2))
    folder = BASE_DIR / "test_images/extended"
    for name, factory, pattern in [
        (
            "helmet",
            lambda: OfflineHelmet(BASE_DIR / "models/motorcycle_helmet/helmet.pt"),
            "helmet_*.jpg",
        ),
        ("number_plate", NumberPlateDetector, "plate.png"),
        ("accident", AccidentDetector, "accident_*.jpg"),
    ]:
        model = factory()
        samples = []
        for path in sorted(folder.glob(pattern)):
            frame = cv2.imread(str(path))
            predictions = model.predict(frame)
            if name == "helmet":
                predictions = [
                    {
                        "label": p["class"],
                        "confidence": p["confidence"],
                        "bbox_xyxy": [
                            p["x"] - p["width"] / 2,
                            p["y"] - p["height"] / 2,
                            p["x"] + p["width"] / 2,
                            p["y"] + p["height"] / 2,
                        ],
                    }
                    for p in predictions["predictions"]
                ]
            samples.append({"file": path.name, "detections": predictions})
            draw(frame, predictions, out / path.name)
        report[name] = {"demo_only": True, "samples": samples}
        print(
            name,
            "images",
            len(samples),
            "boxes",
            sum(len(s["detections"]) for s in samples),
            flush=True,
        )
        (out / "report.json").write_text(json.dumps(report, indent=2))
        del model
        gc.collect()


if __name__ == "__main__":
    main()
