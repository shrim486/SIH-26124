"""Shared paths and validation for the single-class pothole pipeline."""
import argparse
import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
DATA_YAML = BASE_DIR / "dataset" / "data.yaml"
MODEL_PATH = BASE_DIR / "models" / "road_hazards" / "pothole" / "best.pt"
RUNS_DIR = BASE_DIR / "outputs"
# Keep library settings and generated artifacts within this project.
(BASE_DIR / ".ultralytics").mkdir(parents=True, exist_ok=True)
os.environ.setdefault("YOLO_CONFIG_DIR", str(BASE_DIR / ".ultralytics"))
os.environ.setdefault("YOLO_AUTOINSTALL", "false")


def project_path(value):
    path = Path(value).expanduser()
    return path.resolve() if path.is_absolute() else (BASE_DIR / path).resolve()


def positive_int(value):
    result = int(value)
    if result <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return result


def probability(value):
    result = float(value)
    if not 0 <= result <= 1:
        raise argparse.ArgumentTypeError("must be between 0 and 1")
    return result


def run_name(value):
    if not value or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_-" for c in value):
        raise argparse.ArgumentTypeError("use letters, numbers, underscores or hyphens")
    return value


def select_device(requested="auto"):
    import torch
    device = ("0" if torch.cuda.is_available() else "cpu") if requested == "auto" else requested
    if device != "cpu" and (not device.isdigit() or not torch.cuda.is_available()
                            or int(device) >= torch.cuda.device_count()):
        raise ValueError("Device must be cpu or an available CUDA GPU index (for example 0).")
    print("Device:", f"CUDA {device}: {torch.cuda.get_device_name(int(device))}" if device != "cpu" else "CPU")
    return device


def validate_names(names):
    if isinstance(names, list):
        names = dict(enumerate(names))
    if not isinstance(names, dict) or set(names) != {0} or str(names[0]).lower() not in {"pothole", "potholes"}:
        raise ValueError("Expected exactly one class: 0 = pothole (or potholes). Do not relabel a multi-class dataset.")
    return names


def load_detector(weights):
    path = project_path(weights)
    if not path.is_file():
        raise FileNotFoundError(f"Trained weights not found: {path}. Run train.py after preparing the dataset.")
    from ultralytics import YOLO
    model = YOLO(str(path))
    if model.task != "detect":
        raise ValueError("Expected object-detection weights.")
    validate_names(model.names)
    return model
