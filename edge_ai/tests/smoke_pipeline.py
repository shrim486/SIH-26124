"""Optional end-to-end SOFTWARE check on tiny synthetic fixtures, not accuracy."""
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from edge_ai.config.config import BASE_DIR, RUNS_DIR
import cv2
import numpy as np
import yaml
from PIL import Image, ImageDraw
from edge_ai.training import evaluate
from edge_ai.processing import inference_manager as predict
from edge_ai.training import train


def main():
    print("SOFTWARE VERIFICATION ONLY: synthetic fixtures, no pothole accuracy claim.", flush=True)
    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    fixture = Path(tempfile.mkdtemp(prefix="software_verification_", dir=RUNS_DIR))
    for split_index, split in enumerate(("train", "valid", "test")):
        for folder in ("images", "labels"):
            (fixture / "dataset" / split / folder).mkdir(parents=True)
        for i in range(2):
            image = Image.new("RGB", (64, 64), (40 + split_index * 40, 70 + i * 20, 90))
            ImageDraw.Draw(image).rectangle((20, 20, 44, 44), fill=(10 + i, 10, 10))
            image.save(fixture / "dataset" / split / "images" / f"fixture_{i}.png")
            (fixture / "dataset" / split / "labels" / f"fixture_{i}.txt").write_text("0 0.5 0.5 0.375 0.375\n")
    config = fixture / "dataset" / "data.yaml"
    config.write_text(yaml.safe_dump({"train": "train/images", "val": "valid/images",
                                     "test": "test/images", "nc": 1, "names": ["pothole"]}))
    train.RUNS_DIR = fixture / "training"
    evaluate.RUNS_DIR = fixture / "evaluation"
    predict.RUNS_DIR = fixture
    train.train_model(smoke_test=True, data=config, imgsz=64, batch=2, device="cpu", name="synthetic_only")
    weights = fixture / "training/synthetic_only/weights/best.pt"
    assert weights.is_file()
    evaluate.evaluate_model(weights=weights, data=config, imgsz=64, batch=2, device="cpu", name="synthetic_only")
    output = predict.detect(str(fixture / "dataset/test/images/fixture_0.png"),
                            weights=weights, imgsz=64, device="cpu", name="synthetic_image")
    assert len((output / "detections.jsonl").read_text().splitlines()) == 1
    video = fixture / "synthetic_clip.avi"
    writer = cv2.VideoWriter(str(video), cv2.VideoWriter_fourcc(*"MJPG"), 3, (64, 64))
    assert writer.isOpened()
    for i in range(3):
        writer.write(np.full((64, 64, 3), 50 + i * 30, dtype=np.uint8))
    writer.release()
    output = predict.detect(str(video), weights=weights, imgsz=64, device="cpu", name="synthetic_video")
    records = [json.loads(line) for line in (output / "detections.jsonl").read_text().splitlines()]
    assert len(records) == 3, len(records)
    videos = list(output.glob("*.avi")) + list(output.glob("*.mp4"))
    assert videos
    capture = cv2.VideoCapture(str(videos[0]))
    assert capture.isOpened() and int(capture.get(cv2.CAP_PROP_FRAME_COUNT)) == 3
    capture.release()
    summary = {"purpose": "software verification using synthetic fixtures only", "training": "passed",
               "evaluation": "passed", "image_output": "passed", "video_output": "3 frames saved and readable",
               "pothole_model_trained": False}
    (fixture / "verification.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))
    print("Verification artifacts:", fixture)


if __name__ == "__main__":
    main()
