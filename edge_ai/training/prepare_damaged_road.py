"""Convert RDD2022 Pascal VOC annotations to one-class YOLO labels."""
import random
import shutil
import xml.etree.ElementTree as ET
from pathlib import Path

import yaml
from PIL import Image

BASE_DIR = Path(__file__).resolve().parents[1]
RAW_DIR = BASE_DIR / "dataset" / "damaged_road" / "raw" / "rdd2022_india"
DATASET_DIR = BASE_DIR / "dataset" / "damaged_road"
TARGET_CLASSES = {"D00", "D10", "D20"}


def convert_annotation(xml_path, image_path):
    with Image.open(image_path) as image:
        width, height = image.size
    labels = []
    for item in ET.parse(xml_path).getroot().findall("object"):
        if (item.findtext("name") or "").upper() not in TARGET_CLASSES:
            continue
        box = item.find("bndbox")
        if box is None:
            continue
        xmin, ymin = float(box.findtext("xmin")), float(box.findtext("ymin"))
        xmax, ymax = float(box.findtext("xmax")), float(box.findtext("ymax"))
        xmin, xmax = sorted((max(0, xmin), min(width, xmax)))
        ymin, ymax = sorted((max(0, ymin), min(height, ymax)))
        if xmax <= xmin or ymax <= ymin:
            continue
        labels.append(f"0 {(xmin + xmax) / (2 * width):.6f} {(ymin + ymax) / (2 * height):.6f} {(xmax - xmin) / width:.6f} {(ymax - ymin) / height:.6f}")
    return labels


def prepare(seed=42):
    images = {p.stem: p for p in RAW_DIR.rglob("*") if p.suffix.lower() in {".jpg", ".jpeg", ".png"}}
    xmls = {p.stem: p for p in RAW_DIR.rglob("*.xml")}
    pairs = [(images[key], xmls[key]) for key in sorted(images.keys() & xmls.keys())]
    if not pairs:
        raise FileNotFoundError(f"No image/XML pairs found under {RAW_DIR}")
    random.Random(seed).shuffle(pairs)
    split_at, valid_at = int(len(pairs) * 0.7), int(len(pairs) * 0.85)
    for split, group in (("train", pairs[:split_at]), ("valid", pairs[split_at:valid_at]), ("test", pairs[valid_at:])):
        image_dir, label_dir = DATASET_DIR / split / "images", DATASET_DIR / split / "labels"
        image_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for image, xml in group:
            target = image_dir / image.name
            shutil.copy2(image, target)
            (label_dir / f"{image.stem}.txt").write_text("\n".join(convert_annotation(xml, image)) + "\n", encoding="utf-8")
    (DATASET_DIR / "data.yaml").write_text(yaml.safe_dump({"path": ".", "train": "train/images", "val": "valid/images", "test": "test/images", "nc": 1, "names": {0: "damaged_road"}}, sort_keys=False), encoding="utf-8")
    print(f"Prepared {len(pairs)} labelled RDD image pairs under {DATASET_DIR}")


if __name__ == "__main__":
    prepare()
