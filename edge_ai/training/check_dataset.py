"""Validate real YOLO detection labels, image files and split isolation."""
import argparse
import hashlib
import json
import math
from pathlib import Path

import yaml
from PIL import Image

from edge_ai.config.config import DATA_YAML, project_path, validate_names

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff"}


def load_config(data_yaml):
    path = project_path(data_yaml)
    if not path.is_file():
        raise FileNotFoundError(f"Dataset YAML not found: {path}")
    config = yaml.safe_load(path.read_text(encoding="utf-8-sig"))
    if not isinstance(config, dict):
        raise ValueError("Dataset YAML must contain a mapping.")
    validate_names(config.get("names"))
    if config.get("nc", 1) != 1:
        raise ValueError("Dataset nc must equal 1.")
    root = Path(config.get("path") or path.parent)
    if not root.is_absolute():
        root = path.parent / root
    root = root.resolve()
    resolved = {"path": str(root), "nc": 1, "names": config["names"]}
    for split in ("train", "val", "test"):
        value = config.get(split)
        if value is None:
            continue
        if not isinstance(value, str):
            raise ValueError(f"{split}: expected one images directory, not a list or file manifest.")
        directory = (root / value).resolve()
        # Roboflow exports sometimes prefix split paths with ../.
        if not directory.exists() and value.startswith("../"):
            directory = (root / value[3:]).resolve()
        if directory.name != "images":
            raise ValueError(f"{split}: expected a directory ending in images: {directory}")
        resolved[split] = str(directory)
    return resolved


def check_dataset(data_yaml=DATA_YAML, required_splits=("train", "val", "test")):
    config = load_config(data_yaml)
    report = {"data": str(project_path(data_yaml)), "splits": {}, "errors": [], "warnings": []}
    seen_hashes = {}
    for split in required_splits:
        if split not in config:
            report["errors"].append(f"Missing {split} entry in dataset YAML.")
            continue
        image_dir = Path(config[split])
        label_dir = image_dir.parent / "labels"
        if not image_dir.is_dir() or not label_dir.is_dir():
            report["errors"].append(f"{split}: missing images/labels directories under {image_dir.parent}")
            continue
        images = sorted(p for p in image_dir.rglob("*") if p.is_file() and p.suffix.lower() in IMAGE_EXTENSIONS)
        labels = {p.relative_to(label_dir) for p in label_dir.rglob("*.txt")}
        expected = set()
        stats = {"images": len(images), "label_files": len(labels), "boxes": 0, "negative_images": 0}
        report["splits"][split] = stats
        if not images:
            report["errors"].append(f"{split}: no images. Download and extract the YOLOv8 dataset first.")
        for image in images:
            relative = image.relative_to(image_dir).with_suffix(".txt")
            if relative in expected:
                report["errors"].append(f"{split}: multiple images share annotation {relative}")
            expected.add(relative)
            label = label_dir / relative
            try:
                with Image.open(image) as im:
                    im.load()
                    if min(im.size) < 10:
                        raise ValueError("image is smaller than 10 pixels")
                    # Hash decoded pixels to also catch identical images with different metadata.
                    rgb = im.convert("RGB")
                    digest = hashlib.sha256(str(rgb.size).encode() + rgb.tobytes()).hexdigest()
                previous = seen_hashes.get(digest)
                if previous and previous[0] != split:
                    report["errors"].append(f"Split leakage: {image} duplicates {previous[1]}")
                elif previous:
                    report["warnings"].append(f"Duplicate image within {split}: {image.name}")
                else:
                    seen_hashes[digest] = (split, str(image))
            except (OSError, ValueError) as exc:
                report["errors"].append(f"Unreadable image {image}: {exc}")
            if not label.is_file():
                report["errors"].append(f"Missing label: {label}. Use an empty .txt only for a verified negative image.")
                continue
            try:
                lines = [line.strip() for line in label.read_text(encoding="utf-8-sig").splitlines() if line.strip()]
            except (OSError, UnicodeError) as exc:
                report["errors"].append(f"Cannot read {label}: {exc}")
                continue
            if not lines:
                stats["negative_images"] += 1
            for number, line in enumerate(lines, 1):
                try:
                    values = line.split()
                    if len(values) != 5:
                        raise ValueError("expected class xc yc width height (5 values)")
                    if int(values[0]) != 0:
                        raise ValueError("class must be 0")
                    x, y, w, h = map(float, values[1:])
                    if not all(math.isfinite(v) and 0 <= v <= 1 for v in (x, y, w, h)) or w <= 0 or h <= 0:
                        raise ValueError("coordinates must be finite and normalized; width/height must be positive")
                    if x-w/2 < -1e-5 or y-h/2 < -1e-5 or x+w/2 > 1+1e-5 or y+h/2 > 1+1e-5:
                        raise ValueError("bounding box extends outside image")
                    stats["boxes"] += 1
                except ValueError as exc:
                    report["errors"].append(f"{label}:{number}: {exc}")
        for orphan in sorted(labels - expected):
            report["errors"].append(f"Orphan label without image: {label_dir / orphan}")
        if images and stats["boxes"] == 0:
            report["errors"].append(f"{split}: no valid pothole boxes; cannot train/evaluate this split.")
    return config, report


def print_report(report):
    for name, stats in report["splits"].items():
        print(f"{name}: " + ", ".join(f"{key}={value}" for key, value in stats.items()))
    for level in ("warnings", "errors"):
        for message in report[level][:25]:
            print(f"{level.upper()}: {message}")
        if len(report[level]) > 25:
            print(f"... {len(report[level])-25} more {level}; use --report for full details")
    print(f"Dataset check: {len(report['errors'])} errors, {len(report['warnings'])} warnings")


def require_dataset(data_yaml=DATA_YAML):
    config, report = check_dataset(data_yaml)
    print_report(report)
    if report["errors"]:
        raise ValueError("Dataset validation failed. Fix the reported issues before continuing.")
    return config


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", default=str(DATA_YAML))
    parser.add_argument("--report", help="Optional JSON report path, relative to edge_ai")
    args = parser.parse_args()
    try:
        _, report = check_dataset(args.data)
        print_report(report)
        if args.report:
            target = project_path(args.report)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(report, indent=2), encoding="utf-8")
        raise SystemExit(bool(report["errors"]))
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
