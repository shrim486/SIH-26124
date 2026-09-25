"""Check damaged-road YOLO images, labels, and normalized boxes."""
from pathlib import Path

from PIL import Image

BASE_DIR = Path(__file__).resolve().parents[1]
DATASET_DIR = BASE_DIR / "dataset" / "damaged_road"
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}


def check():
    errors = []
    for split in ("train", "valid", "test"):
        images = [p for p in (DATASET_DIR / split / "images").glob("*")
              if p.suffix.lower() in IMAGE_EXTENSIONS]
        labels = DATASET_DIR / split / "labels"
        if not images:
            errors.append(f"{split}: no images")
        for image in images:
            with Image.open(image) as opened:
                opened.load()
            label = labels / f"{image.stem}.txt"
            if not label.is_file():
                errors.append(f"missing label: {label}")
                continue
            for number, line in enumerate(label.read_text(encoding="utf-8").splitlines(), 1):
                values = line.split()
                if len(values) != 5 or values[0] != "0" or any(not 0 < float(value) < 1 for value in values[1:]):
                    errors.append(f"invalid label: {label}:{number}")
        print(f"{split}: {len(images)} images")
    if errors:
        raise ValueError("\n".join(errors[:20]))
    print("Damaged-road dataset is valid")


if __name__ == "__main__":
    check()
