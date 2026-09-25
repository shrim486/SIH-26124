"""Extract spaced dashcam frames for damaged-road annotation."""
import argparse
from pathlib import Path

import cv2

BASE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE = BASE_DIR / "test_videos" / "dashcam" / "candidate.mp4"
DEFAULT_OUTPUT = BASE_DIR / "dataset" / "damaged_road" / "raw" / "dashcam_frames"


def extract(source=DEFAULT_SOURCE, output=DEFAULT_OUTPUT, every_seconds=0.5):
    source, output = Path(source).resolve(), Path(output).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Dashcam video not found: {source}")
    if every_seconds <= 0:
        raise ValueError("every_seconds must be positive")
    capture = cv2.VideoCapture(str(source))
    if not capture.isOpened():
        raise OSError(f"Could not open dashcam video: {source}")
    fps = capture.get(cv2.CAP_PROP_FPS) or 1
    interval = max(1, round(fps * every_seconds))
    output.mkdir(parents=True, exist_ok=True)
    index = saved = 0
    while True:
        ok, frame = capture.read()
        if not ok:
            break
        if index % interval == 0:
            target = output / f"dashcam_{index:06d}_{index / fps:.2f}s.jpg"
            if not cv2.imwrite(str(target), frame):
                raise OSError(f"Could not write {target}")
            saved += 1
        index += 1
    capture.release()
    print(f"Extracted {saved} frames from {index} dashcam frames into {output}")
    print("Annotate damaged surfaces, then create matching YOLO .txt files before training.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", default=str(DEFAULT_SOURCE))
    parser.add_argument("--output", default=str(DEFAULT_OUTPUT))
    parser.add_argument("--every-seconds", type=float, default=0.5)
    extract(**vars(parser.parse_args()))
