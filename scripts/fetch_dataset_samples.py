"""Download small real labeled subsets, preserving upstream splits and provenance.

These are pipeline-development subsets, not representative accuracy benchmarks.
"""

import argparse
import hashlib
import json
from pathlib import Path
from urllib.parse import quote
import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = Path(__file__).resolve().parents[1] / "edge_ai/dataset"
CROSSWALK_REPO = "piranha9827/Crosswalks-Detection-using-YOLO"
CROSSWALK_REV = "df8d3ffc18692975788dcc90de174581e4fcb214"
SESSION = requests.Session()
SESSION.mount(
    "https://",
    HTTPAdapter(
        max_retries=Retry(
            total=3, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504]
        )
    ),
)


def get(url, **kwargs):
    response = SESSION.get(url, timeout=60, **kwargs)
    response.raise_for_status()
    return response


def save_sample(folder, split, stem, image, labels, seen):
    digest = hashlib.sha256(image).hexdigest()
    if digest in seen:
        return False
    seen.add(digest)
    for part in ("images", "labels"):
        (folder / split / part).mkdir(parents=True, exist_ok=True)
    image_path = folder / split / "images" / f"{stem}.jpg"
    label_path = folder / split / "labels" / f"{stem}.txt"
    if image_path.exists() and image_path.read_bytes() != image:
        raise ValueError(f"Local image changed: {image_path}")
    if label_path.exists() and label_path.read_text() != labels:
        raise ValueError(f"Local labels changed: {label_path}")
    if not image_path.exists():
        image_path.write_bytes(image)
    if not label_path.exists():
        label_path.write_text(labels, encoding="utf-8")
    return True


def fetch(name, limit, resume=False):
    folder = ROOT / name
    if folder.exists() and not resume:
        raise FileExistsError(
            f"Use --resume to continue {folder} without replacing local edits"
        )
    folder.mkdir(parents=True, exist_ok=True)
    seen = set()
    provenance = {"development_subset": True, "limit_per_split": limit, "samples": []}
    if name == "traffic_sign":
        dataset = "keremberke/german-traffic-sign-detection"
        provenance["source"] = "https://huggingface.co/datasets/" + dataset
        provenance["mapping"] = (
            "All 43 traffic-sign types mapped to class 0=traffic_sign; original categories preserved in this manifest."
        )
        for split, remote in [
            ("train", "train"),
            ("valid", "validation"),
            ("test", "test"),
        ]:
            payload = get(
                "https://datasets-server.huggingface.co/first-rows",
                params={"dataset": dataset, "config": "full", "split": remote},
            ).json()
            count = 0
            for item in payload["rows"]:
                row = item["row"]
                w, h = row["width"], row["height"]
                lines = []
                for x, y, bw, bh in row["objects"]["bbox"]:
                    left, top = max(0, x), max(0, y)
                    right, bottom = min(w, x + bw), min(h, y + bh)
                    if right <= left or bottom <= top:
                        continue
                    lines.append(
                        f"0 {(left+right)/2/w:.8f} {(top+bottom)/2/h:.8f} {(right-left)/w:.8f} {(bottom-top)/h:.8f}"
                    )
                image = get(row["image"]["src"]).content
                stem = str(row["image_id"])
                if save_sample(
                    folder, split, stem, image, "\n".join(lines) + "\n", seen
                ):
                    count += 1
                    provenance["samples"].append(
                        {
                            "split": split,
                            "id": stem,
                            "source_split": remote,
                            "row": item["row_idx"],
                            "original_classes": row["objects"]["category"],
                        }
                    )
                if count >= limit:
                    break
            print(name, split, count, flush=True)
    else:
        tree = get(
            f"https://api.github.com/repos/{CROSSWALK_REPO}/git/trees/{CROSSWALK_REV}?recursive=1"
        ).json()["tree"]
        paths = {entry["path"] for entry in tree}
        provenance.update(
            source=f"https://github.com/{CROSSWALK_REPO}",
            revision=CROSSWALK_REV,
            license="GPL-3.0 (publisher repository)",
        )
        raw = f"https://raw.githubusercontent.com/{CROSSWALK_REPO}/{CROSSWALK_REV}/"
        groups = set()
        for split in ("train", "valid", "test"):
            count = 0
            for entry in tree:
                path = entry["path"]
                if f"/{split}/images/" not in path or not path.endswith(".jpg"):
                    continue
                group = Path(path).stem.split("_jpg")[0]
                if group in groups:
                    continue
                label_path = (
                    path.replace("/images/", "/labels/").rsplit(".", 1)[0] + ".txt"
                )
                if label_path not in paths:
                    continue
                image = get(raw + quote(path)).content
                labels = get(raw + quote(label_path)).text
                if save_sample(folder, split, Path(path).stem, image, labels, seen):
                    groups.add(group)
                    count += 1
                    provenance["samples"].append(
                        {"split": split, "file": path, "group": group}
                    )
                if count >= limit:
                    break
            print(name, split, count, flush=True)
    (folder / "data.yaml").write_text(
        yaml.safe_dump(
            {
                "train": "train/images",
                "val": "valid/images",
                "test": "test/images",
                "names": {0: name},
            },
            sort_keys=False,
        )
    )
    (folder / "provenance.json").write_text(json.dumps(provenance, indent=2))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--datasets",
        nargs="+",
        choices=["traffic_sign", "zebra_crossing"],
        default=["traffic_sign", "zebra_crossing"],
    )
    p.add_argument("--per-split", type=int, default=12)
    p.add_argument("--resume", action="store_true")
    a = p.parse_args()
    if not 1 <= a.per_split <= 100:
        p.error("--per-split must be 1..100")
    for name in a.datasets:
        fetch(name, a.per_split, a.resume)
