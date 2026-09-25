"""Import a downloaded Roboflow YOLOv8 ZIP without changing its split assignments."""
import argparse
import json
import shutil
import tempfile
import zipfile
from pathlib import Path

import yaml

from edge_ai.config.config import BASE_DIR, validate_names
from edge_ai.training.check_dataset import check_dataset, print_report


def import_dataset(archive):
    archive = Path(archive).expanduser().resolve()
    destination = BASE_DIR / "dataset"
    if not archive.is_file():
        raise FileNotFoundError(f"ZIP not found: {archive}")
    for name in ("train", "valid", "val", "test"):
        target = destination / name
        if target.exists() and any(p.is_file() for p in target.rglob("*")):
            raise ValueError(f"Dataset already contains files: {target}. Preserve it before importing another version.")
    with tempfile.TemporaryDirectory(prefix="dataset-import-", dir=BASE_DIR) as temp:
        staging = Path(temp).resolve()
        with zipfile.ZipFile(archive) as bundle:
            for member in bundle.infolist():
                target = (staging / member.filename).resolve()
                if not target.is_relative_to(staging):
                    raise ValueError(f"Unsafe path in ZIP: {member.filename}")
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise ValueError("ZIP symlinks are not supported.")
            bundle.extractall(staging)
        yamls = list(staging.rglob("data.yaml"))
        if len(yamls) != 1:
            raise ValueError("Expected exactly one data.yaml in a YOLOv8 detection export.")
        original_yaml = yamls[0]
        original_text = original_yaml.read_text(encoding="utf-8-sig")
        config = yaml.safe_load(original_text)
        if not isinstance(config, dict):
            raise ValueError("Invalid dataset YAML.")
        validate_names(config.get("names"))
        if config.get("nc", 1) != 1:
            raise ValueError("Dataset has multiple classes.")
        root = original_yaml.parent
        # Only accept the documented Roboflow directory layouts.
        val_name = "valid" if (root / "valid" / "images").is_dir() else "val"
        normalized = {"train": "train/images", "val": f"{val_name}/images",
                      "test": "test/images", "nc": 1, "names": config["names"]}
        original_yaml.write_text(yaml.safe_dump(normalized, sort_keys=False), encoding="utf-8")
        _, report = check_dataset(original_yaml)
        print_report(report)
        if report["errors"]:
            raise ValueError("Dataset failed validation; no imported files were copied into dataset/.")
        destination.mkdir(parents=True, exist_ok=True)
        for name in ("train", val_name, "test"):
            shutil.copytree(root / name, destination / name, dirs_exist_ok=True)
        (destination / "data.original.yaml").write_text(original_text, encoding="utf-8")
        (destination / "data.yaml").write_text(yaml.safe_dump(normalized, sort_keys=False), encoding="utf-8")
        for readme in root.glob("README*"):
            if readme.is_file():
                shutil.copy2(readme, destination / ("source-" + readme.name))
        provenance = {"archive": str(archive), "format": "YOLOv8 object detection",
                      "source": "https://public.roboflow.com/object-detection/pothole/1",
                      "splits_preserved": True, "class_names": config["names"]}
        (destination / "import.json").write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print("Dataset imported to:", destination)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archive", help="Path to the downloaded ZIP (relative to your terminal or absolute)")
    args = parser.parse_args()
    try:
        import_dataset(args.archive)
    except (OSError, ValueError, yaml.YAMLError, zipfile.BadZipFile) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
