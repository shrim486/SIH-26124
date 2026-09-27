"""Supervised sign localization with the publisher's original label retained."""

from edge_ai.config.config import BASE_DIR
from pathlib import Path


class TrafficSignDetector:
    def __init__(self, weights=None, confidence=0.35):
        from ultralytics import YOLO

        path = (
            Path(weights) if weights else BASE_DIR / "models/traffic_sign/roboflow.pt"
        )
        if not path.is_file():
            raise FileNotFoundError(
                "Run scripts/fetch_extended_models.py --models traffic_sign"
            )
        self.model = YOLO(str(path))
        expected = {
            "bus_stop",
            "do_not_enter",
            "do_not_stop",
            "do_not_turn_l",
            "do_not_turn_r",
            "do_not_u_turn",
            "enter_left_lane",
            "green_light",
            "left_right_lane",
            "no_parking",
            "parking",
            "ped_crossing",
            "ped_zebra_cross",
            "railway_crossing",
            "red_light",
            "stop",
            "t_intersection_l",
            "traffic_light",
            "u_turn",
            "warning",
            "yellow_light",
        }
        if set(self.model.names.values()) != expected:
            raise ValueError(
                "Traffic-sign checkpoint taxonomy does not match the documented source"
            )
        self.confidence = confidence

    def predict(self, frame):
        predictions = []
        for box in self.model.predict(frame, conf=self.confidence, verbose=False)[
            0
        ].boxes:
            label = self.model.names[int(box.cls.item())]
            if label in {"green_light", "red_light", "yellow_light", "traffic_light"}:
                continue
            predictions.append(
                {
                    "label": "traffic_sign",
                    "model_label": label,
                    "confidence": float(box.conf.item()),
                    "bbox_xyxy": box.xyxy[0].tolist(),
                }
            )
        return predictions
