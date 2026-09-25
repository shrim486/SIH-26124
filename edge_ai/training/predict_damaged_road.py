"""Run the damaged-road model on an image, video, or webcam source."""
import argparse
from pathlib import Path

from ultralytics import YOLO

BASE_DIR = Path(__file__).resolve().parents[1]
MODEL = BASE_DIR / "models" / "road_hazards" / "damaged_road" / "best.pt"
RDD_DAMAGE_CLASSES = {"D00", "D10", "D20"}


def predict(source, weights=MODEL, confidence=0.4, name="damaged_road_prediction", device="cpu"):
    source = Path(source)
    if not source.is_absolute():
        source = BASE_DIR / source
    weights = Path(weights).resolve()
    if not weights.is_file():
        raise FileNotFoundError(f"Damaged-road weights not found: {weights}")
    model = YOLO(str(weights))
    class_ids = [index for index, name in model.names.items()
                 if str(name).upper() in RDD_DAMAGE_CLASSES or str(name).lower() == "damaged_road"]
    if not class_ids:
        raise ValueError("Weights contain no damaged-road classes")
    return model.predict(source=str(source), conf=confidence, classes=class_ids, device=device,
                                      save=True, project=str(BASE_DIR / "outputs"), name=name,
                                      exist_ok=False, verbose=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--weights", default=str(MODEL))
    parser.add_argument("--confidence", type=float, default=0.4)
    parser.add_argument("--name", default="damaged_road_prediction")
    parser.add_argument("--device", default="cpu")
    predict(**vars(parser.parse_args()))
