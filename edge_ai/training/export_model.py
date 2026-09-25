"""Optional ONNX export of trained pothole weights."""
import argparse

from edge_ai.config.config import MODEL_PATH, load_detector, positive_int


def export_model(weights=MODEL_PATH, imgsz=640):
    model = load_detector(weights)
    path = model.export(format="onnx", imgsz=imgsz, device="cpu", simplify=False)
    print("Exported:", path)
    return path


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", default=str(MODEL_PATH))
    parser.add_argument("--imgsz", type=positive_int, default=640)
    args = parser.parse_args()
    try:
        export_model(**vars(args))
    except (OSError, ValueError, ImportError) as exc:
        parser.exit(1, f"ERROR: {exc}\nFor ONNX export install requirements-export.txt first.\n")
