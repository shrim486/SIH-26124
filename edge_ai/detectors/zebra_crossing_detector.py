"""Supervised YOLO crosswalk checkpoint; preserves publisher class metadata."""

from edge_ai.config.config import BASE_DIR


class ZebraCrossingDetector:
    def __init__(self, confidence=0.35):
        from ultralytics import YOLO

        path = BASE_DIR / "models/zebra_crossing/best.pt"
        if not path.is_file():
            raise FileNotFoundError(
                "Fetch zebra_crossing with scripts/fetch_extended_models.py"
            )
        self.model = YOLO(str(path))
        if len(self.model.names) != 1:
            raise ValueError(f"Expected single crosswalk class: {self.model.names}")
        self.confidence = confidence

    def predict(self, frame):
        result = self.model.predict(
            frame, conf=self.confidence, verbose=False, device="cpu"
        )[0]
        return [
            {
                "label": "zebra_crossing",
                "model_label": self.model.names[int(b.cls.item())],
                "confidence": float(b.conf.item()),
                "bbox_xyxy": b.xyxy[0].tolist(),
            }
            for b in result.boxes
        ]
