"""Open-vocabulary road-scene baseline; outputs are candidates, not validated labels."""

from pathlib import Path
import hashlib
import json
from edge_ai.config.config import BASE_DIR

PROMPTS = {
    "waterlogging": ["water puddle on road", "flooded road"],
    "road_divider": [
        "concrete road divider",
        "road median barrier",
        "metal road guardrail",
    ],
    "zebra_crossing": ["zebra crossing", "pedestrian crosswalk"],
    "traffic_sign": ["traffic sign", "stop sign", "speed limit sign"],
}


class RoadSceneDetector:
    def __init__(self, tasks=None, confidence=0.25):
        from ultralytics import YOLOWorld
        import ultralytics.nn.text_model as text_model

        text_model.WEIGHTS_DIR = BASE_DIR / "models" / "road_scene"
        tasks = list(tasks or PROMPTS)
        self.prompts = [prompt for task in tasks for prompt in PROMPTS[task]]
        self.categories = [task for task in tasks for _ in PROMPTS[task]]
        source = BASE_DIR / "models/road_scene/yolov8s-worldv2.pt"
        if not source.is_file():
            raise FileNotFoundError(
                "Run scripts/fetch_extended_models.py --models road_scene"
            )
        key = hashlib.sha256(json.dumps(self.prompts).encode()).hexdigest()[:12]
        cache = source.with_name(f"prompts_{key}.pt")
        if cache.is_file():
            self.model = YOLOWorld(str(cache))
        else:
            self.model = YOLOWorld(str(source))
            self.model.set_classes(self.prompts)
            if hasattr(self.model.model, "clip_model"):
                del self.model.model.clip_model
            self.model.save(str(cache))
        self.confidence = confidence

    def predict(self, frame):
        result = self.model.predict(
            frame, conf=self.confidence, verbose=False, device="cpu"
        )[0]
        boxes = []
        for box in result.boxes:
            index = int(box.cls.item())
            boxes.append(
                {
                    "label": self.categories[index],
                    "prompt": self.prompts[index],
                    "confidence": float(box.conf.item()),
                    "bbox_xyxy": box.xyxy[0].tolist(),
                    "status": "zero_shot_candidate",
                }
            )
        return boxes
