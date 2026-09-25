"""Train the separate single-class damaged-road detection model."""
import argparse
from pathlib import Path

import yaml
from ultralytics import YOLO


DEFAULT_DATA = Path(__file__).resolve().parents[1] / "dataset" / "damaged_road" / "data.yaml"
DEFAULT_WEIGHTS = Path(__file__).resolve().parents[1] / "models" / "pretrained" / "yolov8n.pt"
DEFAULT_RUNS = Path(__file__).resolve().parents[1] / "outputs" / "damaged_road_training"


def train(data=DEFAULT_DATA, weights=DEFAULT_WEIGHTS, epochs=100, imgsz=640,
          batch=4, name="damaged_road_v1", device="cpu"):
    data = Path(data).resolve()
    weights = Path(weights).resolve()
    if not data.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {data}")
    if not weights.is_file():
        raise FileNotFoundError(f"Starting weights not found: {weights}")
    config = yaml.safe_load(data.read_text(encoding="utf-8"))
    if not isinstance(config, dict) or config.get("names") != {0: "damaged_road"}:
        raise ValueError("Damaged-road data.yaml must define exactly one class: damaged_road")
    model = YOLO(str(weights))
    return model.train(data=str(data), epochs=epochs, imgsz=imgsz, batch=batch,
                       project=str(DEFAULT_RUNS), name=name, device=device,
                       workers=0, patience=25, plots=True, save=True, seed=42)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(DEFAULT_DATA))
    parser.add_argument("--weights", default=str(DEFAULT_WEIGHTS))
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--batch", type=int, default=4)
    parser.add_argument("--name", default="damaged_road_v1")
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()
    train(**vars(args))
