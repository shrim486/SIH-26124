"""Local helmet/no-helmet inference with the cloud adapter's response schema."""

from pathlib import Path
from ultralytics import YOLO


class OfflineHelmet:
    def __init__(self, weights):
        if not Path(weights).is_file():
            raise FileNotFoundError(
                "Run python scripts/fetch_extended_models.py --models helmet first"
            )
        self.model = YOLO(str(weights))
        self.labels = {}
        for index, label in self.model.names.items():
            normalized = str(label).lower().replace("-", "_").replace(" ", "_")
            if normalized in {"helmet", "with_helmet"}:
                self.labels[index] = "with_helmet"
            elif normalized in {
                "no_helmet",
                "without_helmet",
                "nohelmet",
                "withouthelmet",
            }:
                self.labels[index] = "without_helmet"
        if set(self.labels.values()) != {"with_helmet", "without_helmet"}:
            raise ValueError(
                f"Expected explicit helmet and no-helmet labels; got {self.model.names}"
            )

    def predict(self, crop, confidence=50, overlap=30):
        predictions = []
        result = self.model.predict(
            crop, conf=confidence / 100, verbose=False, device="cpu"
        )[0]
        for box in result.boxes:
            label = self.labels.get(int(box.cls.item()))
            if label is None:
                continue
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            predictions.append(
                {
                    "class": label,
                    "confidence": float(box.conf.item()),
                    "x": (x1 + x2) / 2,
                    "y": (y1 + y2) / 2,
                    "width": x2 - x1,
                    "height": y2 - y1,
                }
            )
        return {"predictions": predictions}
