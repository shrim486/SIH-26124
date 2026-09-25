"""Run a local video demonstration with annotated MP4s and per-frame records."""
import argparse
import hashlib
import json
import time
from pathlib import Path

import cv2
import imageio_ffmpeg
from PIL import Image, ImageDraw

from edge_ai.config.config import load_detector, positive_int, probability, project_path
from edge_ai.processing.inference_manager import detection_record


from edge_ai.cameras.camera_manager import video_info


def run_video(model, source, output, confidence, stride=1):
    info = video_info(source)
    expected_frames = info["frames"] // stride
    if expected_frames < 1:
        raise ValueError("Frame stride exceeds the video length")
    output_fps = info["fps"] / stride
    output.mkdir(parents=True, exist_ok=False)
    video_path = output / "annotated.mp4"
    encoder = imageio_ffmpeg.write_frames(
        str(video_path), (info["width"], info["height"]),
        pix_fmt_in="bgr24", pix_fmt_out="yuv420p", fps=output_fps,
        codec="libx264", quality=None, macro_block_size=1,
        ffmpeg_log_level="error",
        output_params=["-crf", "20", "-preset", "fast", "-movflags", "+faststart"],
    )
    encoder.send(None)
    targets = {int((expected_frames - 1) * fraction) for fraction in (0.2, 0.5, 0.8)}
    snapshots = []
    counts, scores = [], []
    started = time.perf_counter()
    results = model.predict(
        source=str(source), conf=confidence, imgsz=640, device="cpu",
        stream=True, save=False, verbose=False, vid_stride=stride,
    )
    try:
        with (output / "detections.jsonl").open("w", encoding="utf-8") as handle:
            for index, result in enumerate(results):
                # Ultralytics grabs `stride` frames before each retrieve.
                frame_index = (index + 1) * stride - 1
                timestamp = frame_index / info["fps"]
                record = detection_record(result, index)
                record.update(source=str(source), frame_index=frame_index,
                              timestamp_seconds=timestamp)
                handle.write(json.dumps(record, allow_nan=False) + "\n")
                count = len(record["detections"])
                counts.append(count)
                scores.extend(box["confidence"] for box in record["detections"])
                annotated = result.plot(line_width=2, font_size=12)
                cv2.rectangle(annotated, (0, 0), (min(info["width"], 610), 35), (25, 25, 25), -1)
                cv2.putText(annotated, f"{timestamp:.2f}s | candidates: {count} | threshold: {confidence:.2f}",
                            (10, 24), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1, cv2.LINE_AA)
                encoder.send(annotated)
                if index in targets:
                    filename = f"frame_{frame_index:05d}_{timestamp:.2f}s.jpg"
                    if not cv2.imwrite(str(output / filename), annotated):
                        raise OSError(f"Could not write {filename}")
                    snapshots.append((frame_index, result.orig_img.copy(), annotated.copy(), filename))
                if (index + 1) % 25 == 0:
                    print(f"{source.name}: {index + 1}/{expected_frames} sampled frames; {sum(counts)} candidate boxes", flush=True)
                    handle.flush()
    finally:
        results.close()
        encoder.close()
        dataset = getattr(model.predictor, "dataset", None)
        if hasattr(dataset, "close"):
            dataset.close()
        elif getattr(dataset, "cap", None) is not None:
            dataset.cap.release()

    elapsed = time.perf_counter() - started
    if len(counts) != expected_frames:
        raise RuntimeError(f"Decoded {len(counts)} of {expected_frames} expected samples")
    encoded = video_info(video_path)
    if encoded["frames"] != len(counts) or abs(encoded["fps"] - output_fps) > 0.01:
        raise RuntimeError("Output frame count or playback rate differs from the expected sampled stream")

    sheet = Image.new("RGB", (1440, 650), "#111827")
    draw = ImageDraw.Draw(sheet)
    for column, (index, original, annotated, _) in enumerate(snapshots):
        for row, (label, frame) in enumerate((("Original", original), ("Detected candidates", annotated))):
            image = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
            image.thumbnail((480, 290))
            x, y = column * 480, row * 325
            sheet.paste(image, (x + (480 - image.width) // 2, y + 30))
            draw.text((x + 10, y + 8), f"{label} | {index / info['fps']:.2f}s", fill="white")
    sheet.save(output / "preview.jpg", quality=92)
    summary = {
        "source": str(source), "source_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "input": info, "processed_frames": len(counts),
        "frames_with_candidates": sum(count > 0 for count in counts),
        "candidate_boxes_across_frames": sum(counts),
        "maximum_candidates_in_one_frame": max(counts, default=0),
        "confidence_range": [min(scores), max(scores)] if scores else None,
        "confidence_threshold": confidence, "imgsz": 640, "device": "cpu",
        "frame_stride": stride, "analyzed_fps": output_fps,
        "processing_seconds": round(elapsed, 2),
        "annotated_video": str(video_path), "output_video": encoded,
        "snapshots": [entry[3] for entry in snapshots],
        "limitations": "Candidate boxes repeat across sampled frames; these are not unique pothole counts or measured accuracy. No ground-truth labels. Timestamps refer to source frames. Output has no audio. With stride > 1, unsampled frames are not analyzed, playback starts at the first sample, and the incomplete final stride is omitted.",
    }
    (output / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(json.dumps(summary, indent=2), flush=True)
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", nargs="+", required=True, help="Paths relative to edge_ai")
    parser.add_argument("--weights", default="models/road_hazards/pothole/pothole_public_yolov8s_labeled.onnx")
    parser.add_argument("--output", default="outputs/online_video_demo")
    parser.add_argument("--conf", type=probability, default=0.4)
    parser.add_argument("--stride", type=positive_int, default=1,
                        help="Analyze every Nth video frame; 5 gives 5 analyzed FPS for 25 FPS inputs")
    args = parser.parse_args()
    sources = [project_path(source) for source in args.source]
    if len({path.stem for path in sources}) != len(sources):
        parser.error("Source filenames must have distinct stems")
    for source in sources:
        video_info(source)
    output = project_path(args.output)
    output.mkdir(parents=True, exist_ok=False)
    weights = project_path(args.weights)
    model = load_detector(weights)
    summaries = [run_video(model, source, output / source.stem, args.conf, args.stride) for source in sources]
    record = {"weights": str(weights), "weights_sha256": hashlib.sha256(weights.read_bytes()).hexdigest(),
              "class_names": model.names, "videos": summaries}
    (output / "summary.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print("Finished. Results:", output)


if __name__ == "__main__":
    main()
