"""Extract a small set of annotated video frames for the government gallery."""

import argparse
import json
from pathlib import Path
import cv2


def export_frames(run):
    run = Path(run)
    summary = json.loads((run / "summary.json").read_text())
    video = run / "annotated.mp4"
    if not video.is_file():
        return
    cap = cv2.VideoCapture(str(video))
    if not cap.isOpened():
        raise ValueError("Cannot read annotated video")
    fps = cap.get(cv2.CAP_PROP_FPS)
    total = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if fps <= 0 or total != summary["frames_processed"]:
        cap.release()
        raise ValueError("Output metadata does not match summary")
    folder = run / "frames"
    folder.mkdir(exist_ok=True)
    frames = []
    try:
        for index in sorted({round(i * (total - 1) / 4) for i in range(5)}):
            cap.set(cv2.CAP_PROP_POS_FRAMES, index)
            ok, frame = cap.read()
            if not ok:
                raise ValueError(f"Cannot decode frame {index}")
            name = f"frame_{index:06d}.jpg"
            if not cv2.imwrite(str(folder / name), frame):
                raise OSError("Cannot write preview image")
            frames.append({"file": name, "time_seconds": index / fps})
    finally:
        cap.release()
    (folder / "index.json").write_text(json.dumps(frames, indent=2))
    return frames


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", required=True)
    print(json.dumps(export_frames(parser.parse_args().run)))
