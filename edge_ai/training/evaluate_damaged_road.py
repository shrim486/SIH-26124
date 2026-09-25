"""Evaluate the trained damaged-road model on the held-out test split."""
import argparse
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parents[1]
DATA = BASE_DIR / "dataset" / "damaged_road" / "data.yaml"
MODEL = BASE_DIR / "models" / "road_hazards" / "damaged_road" / "best.pt"


def evaluate(weights=MODEL, data=DATA, name="damaged_road_test", device="cpu"):
    weights, data = Path(weights).resolve(), Path(data).resolve()
    if not weights.is_file():
        raise FileNotFoundError(f"Damaged-road weights not found: {weights}")
    return YOLO(str(weights)).val(data=str(data), split="test", project=str(BASE_DIR / "outputs"), name=name, device=device)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", default=str(MODEL))
    parser.add_argument("--data", default=str(DATA))
    parser.add_argument("--name", default="damaged_road_test")
    parser.add_argument("--device", default="cpu")
    evaluate(**vars(parser.parse_args()))
