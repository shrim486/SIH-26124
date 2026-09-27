"""Re-render saved ML predictions with explicit ROI/score filtering, without inference."""

import argparse
import hashlib
import json
from pathlib import Path
import sys
import cv2
import imageio_ffmpeg

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from edge_ai.processing.annotations import filter_detections, draw_frame
from edge_ai.cameras.camera_manager import video_info


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--road-bottom", type=float, default=1.0)
    args = parser.parse_args()
    if not 0 < args.road_bottom <= 1:
        parser.error("--road-bottom must be in (0,1]")
    summary = json.loads((args.run / "summary.json").read_text())
    source = Path(summary["source"])
    info = video_info(source)
    if hashlib.sha256(source.read_bytes()).hexdigest() != summary["source_sha256"]:
        raise ValueError("Source differs from the inference input")
    args.output.mkdir(parents=True, exist_ok=False)
    cap = cv2.VideoCapture(str(source))
    writer = imageio_ffmpeg.write_frames(
        str(args.output / "annotated.mp4"),
        (info["width"], info["height"]),
        fps=info["fps"],
        pix_fmt_in="bgr24",
        codec="libx264",
        macro_block_size=1,
        output_params=["-pix_fmt", "yuv420p", "-movflags", "+faststart"],
        ffmpeg_log_level="error",
    )
    count = boxes = 0
    writer.send(None)
    try:
        with (args.run / "detections.jsonl").open() as predictions, (
            args.output / "detections.jsonl"
        ).open("w") as records:
            for line in predictions:
                row = json.loads(line)
                if row["frame_index"] != count:
                    raise ValueError("Prediction frame indices must be contiguous")
                ok, frame = cap.read()
                if not ok:
                    raise ValueError("Cannot decode matching source frame")
                row["detections"] = filter_detections(
                    row["detections"], info["height"], args.road_bottom
                )
                annotated = draw_frame(
                    frame,
                    row["detections"],
                    row["timestamp_seconds"],
                    row.get("traffic"),
                )
                writer.send(annotated)
                records.write(json.dumps(row) + "\n")
                if count == 0:
                    cv2.imwrite(str(args.output / "preview.jpg"), annotated)
                count += 1
                boxes += len(row["detections"])
    finally:
        cap.release()
        writer.close()
    if count != summary["frames_processed"]:
        raise ValueError("Incomplete prediction records")
    summary.update(
        output=video_info(args.output / "annotated.mp4"),
        boxes_across_frames=boxes,
        road_bottom=args.road_bottom,
        accident_confidence=0.6,
        rendered_from=str(args.run.resolve()),
        note="Original ML predictions preserved in rendered_from; ROI/confidence filtering only. No new inference.",
    )
    (args.output / "summary.json").write_text(json.dumps(summary, indent=2))
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
