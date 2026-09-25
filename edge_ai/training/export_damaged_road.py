"""Export the trained damaged-road model to ONNX."""
import argparse
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL = BASE_DIR / "models" / "road_hazards" / "damaged_road" / "best.pt"


def export(weights=MODEL, imgsz=640):
    weights = Path(weights).resolve()
    if not weights.is_file():
        raise FileNotFoundError(f"Damaged-road weights not found: {weights}")
    return YOLO(str(weights)).export(format="onnx", imgsz=imgsz)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", default=str(MODEL))
    parser.add_argument("--imgsz", type=int, default=640)
    export(**vars(parser.parse_args()))
