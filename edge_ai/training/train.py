"""Fine-tune pretrained YOLOv8n on the validated pothole dataset."""
import argparse
import json
import shutil
import time

import yaml

from edge_ai.config.config import BASE_DIR, DATA_YAML, MODEL_PATH, RUNS_DIR, positive_int, project_path, run_name, select_device
from edge_ai.training.check_dataset import require_dataset


def train_model(smoke_test=False, data=DATA_YAML, epochs=80, imgsz=None, batch=None,
                device="auto", name=None, weights=None):
    config = require_dataset(data)
    device = select_device(device)
    image_size = imgsz or (640 if device != "cpu" else 512)
    batch_size = batch or (8 if device != "cpu" else 4)
    experiment = name or ("pothole_smoke" if smoke_test else "pothole_v1")
    run_dir = RUNS_DIR / run_name(experiment)
    # Reserve a fresh run; never silently overwrite an earlier experiment.
    run_dir.mkdir(parents=True, exist_ok=False)
    resolved_yaml = run_dir / "data.resolved.yaml"
    resolved_yaml.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    from ultralytics import YOLO
    weights_path = project_path(weights) if weights else BASE_DIR / "models" / "pretrained" / "yolov8n.pt"
    if weights and not weights_path.is_file():
        raise FileNotFoundError(f"Pretrained weights not found: {weights_path}")
    model = YOLO(str(weights_path))
    started = time.monotonic()
    results = model.train(
        data=str(resolved_yaml), epochs=1 if smoke_test else epochs, imgsz=image_size,
        batch=batch_size, device=device, patience=20, workers=0, project=str(RUNS_DIR),
        name=experiment, exist_ok=True, plots=True, save=True, seed=42,
    )
    best = model.trainer.best
    if not best.is_file():
        raise RuntimeError(f"Training did not produce best.pt: {best}")
    manifest = {"best_weights": str(best), "smoke_test": smoke_test,
                "elapsed_seconds": round(time.monotonic()-started, 2), "device": device,
                "imgsz": image_size, "batch": batch_size,
                "requested_epochs": 1 if smoke_test else epochs}
    (run_dir / "training_summary.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if not smoke_test:
        MODEL_PATH.parent.mkdir(parents=True, exist_ok=True)
        if MODEL_PATH.exists():
            print(f"Existing {MODEL_PATH.name} preserved. Candidate weights: {best}")
        else:
            shutil.copy2(best, MODEL_PATH)
            print("Model copied to:", MODEL_PATH)
    print("Training complete:", best)
    print("Elapsed seconds:", manifest["elapsed_seconds"])
    return results


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--smoke", action="store_true", help="One epoch; does not promote smoke weights to models/road_hazards/pothole/best.pt")
    parser.add_argument("--data", default=str(DATA_YAML))
    parser.add_argument("--epochs", type=positive_int, default=80)
    parser.add_argument("--imgsz", type=positive_int)
    parser.add_argument("--batch", type=positive_int)
    parser.add_argument("--device", default="auto", help="auto, cpu, or CUDA GPU index")
    parser.add_argument("--name", type=run_name)
    parser.add_argument("--weights", help="Optional local pretrained .pt path")
    args = parser.parse_args()
    try:
        train_model(smoke_test=args.smoke, data=args.data, epochs=args.epochs, imgsz=args.imgsz,
                    batch=args.batch, device=args.device, name=args.name, weights=args.weights)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
