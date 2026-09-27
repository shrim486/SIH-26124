"""Download pinned public checkpoints locally; record hashes and provenance."""

import argparse
import hashlib
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
SOURCES = {
    "traffic_sign": (
        "https://huggingface.co/yahyagul/traffic-sign-yolov8/resolve/15be2681d3b6e666f45c744219aab84e97a2f1b4/best_roboflow.pt",
        "edge_ai/models/traffic_sign/roboflow.pt",
    ),
    "zebra_crossing": (
        "https://raw.githubusercontent.com/piranha9827/Crosswalks-Detection-using-YOLO/df8d3ffc18692975788dcc90de174581e4fcb214/training/training_results/train/weights/best.pt",
        "edge_ai/models/zebra_crossing/best.pt",
    ),
    "helmet": (
        "https://huggingface.co/iam-tsr/yolov8n-helmet-detection/resolve/59b68b03b60314badb0c19ebcc3b95baa8241cf8/best.pt",
        "edge_ai/models/motorcycle_helmet/helmet.pt",
    ),
    "road_scene": (
        "https://github.com/ultralytics/assets/releases/download/v8.3.0/yolov8s-worldv2.pt",
        "edge_ai/models/road_scene/yolov8s-worldv2.pt",
    ),
    "accident": (
        "https://huggingface.co/Enos-123/accident-evaluator-yolov8x/resolve/0fe635a9c3bcd007a1a760e629fe1f8ad65a925c/weights/epoch90.pt",
        "edge_ai/models/accident/best.pt",
    ),
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--models", nargs="+", choices=list(SOURCES), default=list(SOURCES)
    )
    args = parser.parse_args()
    manifest_path = ROOT / "docs/extended-model-assets.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}
    for name in args.models:
        url, relative = SOURCES[name]
        target = ROOT / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            temp = target.with_suffix(".download")
            print("Downloading", name, flush=True)
            with requests.get(url, stream=True, timeout=(15, 90)) as response:
                response.raise_for_status()
                with temp.open("wb") as handle:
                    for block in response.iter_content(1024 * 1024):
                        handle.write(block)
            temp.replace(target)
        digest = hashlib.sha256(target.read_bytes()).hexdigest()
        if name in manifest and manifest[name]["sha256"] != digest:
            raise ValueError(
                f"Existing {name} checkpoint does not match its recorded hash"
            )
        manifest[name] = {
            "url": url,
            "path": relative,
            "sha256": digest,
            "bytes": target.stat().st_size,
            "locally_trained": False,
        }
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
        print(name, target.stat().st_size, digest, flush=True)


if __name__ == "__main__":
    main()
