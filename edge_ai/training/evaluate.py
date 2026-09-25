"""Evaluate the trained detector on held-out test images and save metrics."""
import argparse
import json

import yaml

from edge_ai.config.config import DATA_YAML, MODEL_PATH, RUNS_DIR, load_detector, positive_int, run_name, select_device
from edge_ai.training.check_dataset import require_dataset


def evaluate_model(weights=MODEL_PATH, data=DATA_YAML, imgsz=640, batch=4, device="auto", name="pothole_test"):
    config = require_dataset(data)
    model = load_detector(weights)
    device = select_device(device)
    output = RUNS_DIR / run_name(name)
    output.mkdir(parents=True, exist_ok=False)
    resolved_yaml = output / "data.resolved.yaml"
    resolved_yaml.write_text(yaml.safe_dump(config, sort_keys=False), encoding="utf-8")
    metrics = model.val(data=str(resolved_yaml), split="test", imgsz=imgsz, batch=batch,
                        device=device, workers=0, plots=True, project=str(RUNS_DIR), name=name, exist_ok=True)
    scores = {"precision": float(metrics.box.mp), "recall": float(metrics.box.mr),
              "mAP50": float(metrics.box.map50), "mAP50-95": float(metrics.box.map)}
    (output / "metrics.json").write_text(json.dumps(scores, indent=2), encoding="utf-8")
    for key, value in scores.items():
        print(f"{key}: {value:.4f}")
    print("Evaluation saved to:", output)
    return scores


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--weights", default=str(MODEL_PATH))
    parser.add_argument("--data", default=str(DATA_YAML))
    parser.add_argument("--imgsz", type=positive_int, default=640)
    parser.add_argument("--batch", type=positive_int, default=4)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--name", type=run_name, default="pothole_test")
    args = parser.parse_args()
    try:
        evaluate_model(**vars(args))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
