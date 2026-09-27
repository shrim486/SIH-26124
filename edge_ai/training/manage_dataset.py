"""Validate, train or evaluate a multi-class YOLO detection dataset.

No data is relabeled or synthesized here. Train and validation/test separation
is checked before any model training starts.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import yaml
from PIL import Image


def validate(path):
    path = Path(path).resolve()
    config = yaml.safe_load(path.read_text())
    names = config.get("names")
    if isinstance(names, list):
        names = dict(enumerate(names))
    if not isinstance(names, dict) or set(names) != set(range(len(names))) or not names:
        raise ValueError("names must map contiguous class IDs starting at 0")
    base = (path.parent / config.get("path", ".")).resolve()
    resolved = {"path": str(base), "names": names}
    seen = {}
    counts = {}
    errors = []
    for split in ("train", "val", "test"):
        if split not in config:
            raise ValueError(f"Missing split: {split}")
        images = (base / config[split]).resolve()
        resolved[split] = str(images)
        if images.name != "images":
            raise ValueError("Use split/images folders with matching split/labels")
        files = sorted(
            p
            for p in images.glob("*")
            if p.suffix.lower() in {".jpg", ".jpeg", ".png", ".bmp", ".webp"}
        )
        boxes = 0
        if not files:
            errors.append(f"{split}: no images")
        for image in files:
            with Image.open(image) as opened:
                rgb = opened.convert("RGB")
                digest = hashlib.sha256(
                    str(rgb.size).encode() + rgb.tobytes()
                ).hexdigest()
            if digest in seen and seen[digest] != split:
                errors.append(f"Cross-split duplicate: {image.name}")
            seen[digest] = split
            label = images.parent / "labels" / f"{image.stem}.txt"
            if not label.is_file():
                errors.append(f"Missing label: {label}")
                continue
            for number, line in enumerate(label.read_text().splitlines(), 1):
                if not line.strip():
                    continue
                try:
                    cls, x, y, w, h = map(float, line.split())
                    valid = (
                        all(math.isfinite(v) for v in (cls, x, y, w, h))
                        and cls.is_integer()
                        and int(cls) in names
                    )
                    valid = (
                        valid
                        and 0 < w <= 1
                        and 0 < h <= 1
                        and min(x - w / 2, y - h / 2) >= -1e-6
                        and max(x + w / 2, y + h / 2) <= 1 + 1e-6
                    )
                except (ValueError, TypeError):
                    valid = False
                if not valid:
                    errors.append(f"Invalid box: {label}:{number}")
                boxes += 1
        counts[split] = {"images": len(files), "boxes": boxes}
    if errors:
        raise ValueError("\n".join(errors[:30]))
    return resolved, counts


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("action", choices=["check", "train", "evaluate"])
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--weights", type=Path)
    p.add_argument("--output", type=Path)
    p.add_argument("--epochs", type=int, default=30)
    p.add_argument("--device", default="cpu")
    a = p.parse_args()
    config, counts = validate(a.data)
    print(json.dumps(counts, indent=2))
    if a.action == "check":
        return
    if not a.weights or not a.weights.is_file():
        p.error("Supply trusted local --weights")
    if not a.output:
        p.error("Supply a new --output directory")
    a.output = a.output.resolve()
    a.output.mkdir(parents=True, exist_ok=False)
    resolved = a.output / "data.resolved.yaml"
    resolved.write_text(yaml.safe_dump(config, sort_keys=False))
    from ultralytics import YOLO

    model = YOLO(str(a.weights.resolve()))
    if a.action == "train":
        if a.epochs < 1:
            p.error("--epochs must be positive")
        model.train(
            data=str(resolved),
            epochs=a.epochs,
            device=a.device,
            workers=0,
            batch=4,
            imgsz=640,
            project=str(a.output),
            name="training",
            seed=42,
        )
    else:
        if dict(model.names) != config["names"]:
            raise ValueError(
                f'Model/dataset class mismatch: {model.names} vs {config["names"]}'
            )
        result = model.val(
            data=str(resolved),
            split="test",
            device=a.device,
            workers=0,
            project=str(a.output),
            name="evaluation",
        )
        (a.output / "metrics.json").write_text(
            json.dumps(result.results_dict, indent=2)
        )


if __name__ == "__main__":
    main()
