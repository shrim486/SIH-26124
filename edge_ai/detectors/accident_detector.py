"""Public visual accident detector; does not establish causality or severity."""

from edge_ai.config.config import BASE_DIR


class AccidentDetector:
    def __init__(self, confidence=0.6):
        from ultralytics import YOLO

        path = BASE_DIR / "models/accident/best.pt"
        if not path.is_file():
            raise FileNotFoundError(
                "Run scripts/fetch_extended_models.py --models accident"
            )
        self.model = YOLO(str(path))
        self.confidence = confidence
        # The pinned publisher defines high/medium/low as accident-scene labels.
        # Preserve those source labels; they are not verified medical severity.
        allowed = {
            "accident",
            "crash",
            "collision",
            "car accident",
            "accidents",
            "high",
            "medium",
            "low",
        }
        self.classes = [
            i for i, name in self.model.names.items() if str(name).lower() in allowed
        ]
        if not self.classes:
            raise ValueError(f"No known accident class: {self.model.names}")

    def predict(self, frame):
        result = self.model.predict(
            frame,
            classes=self.classes,
            conf=self.confidence,
            device="cpu",
            verbose=False,
        )[0]
        return [
            {
                "label": "accident_candidate",
                "model_label": self.model.names[int(b.cls.item())],
                "confidence": float(b.conf.item()),
                "bbox_xyxy": b.xyxy[0].tolist(),
                "status": "visual_candidate",
            }
            for b in result.boxes
        ]
