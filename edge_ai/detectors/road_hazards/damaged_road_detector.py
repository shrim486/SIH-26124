"""YOLO damaged-road detector kept separate from the pothole detector."""
from pathlib import Path

from ultralytics import YOLO

RDD_DAMAGE_CLASSES = {"d00", "d10", "d20"}
SINGLE_DAMAGE_CLASS = {"damaged_road"}


class DamagedRoadDetector:
    """Load and run a multi-class damaged-road YOLO model."""

    def __init__(self, weights: str | Path, confidence: float = 0.35):
        if not 0 <= confidence <= 1:
            raise ValueError("confidence must be between 0 and 1")
        self.model = YOLO(str(weights))
        names = {int(index): str(name).lower().replace(" ", "_")
                 for index, name in self.model.names.items()}
        if set(names.values()) == SINGLE_DAMAGE_CLASS:
            self.class_ids = [index for index, name in names.items() if name == "damaged_road"]
        else:
            self.class_ids = [index for index, name in names.items() if name in RDD_DAMAGE_CLASSES]
            if not self.class_ids:
                raise ValueError("Weights must contain damaged_road or RDD2022 classes D00, D10, and D20")
        self.confidence = confidence

    def predict(self, source, **kwargs):
        options = {"conf": self.confidence, "classes": self.class_ids,
               "stream": True, "verbose": False}
        options.update(kwargs)
        return self.model.predict(source=source, **options)
