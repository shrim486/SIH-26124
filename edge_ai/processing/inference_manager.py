"""Stream image, video or webcam detections and save pixel boxes with scores."""
import argparse
import json

from edge_ai.config.config import MODEL_PATH, RUNS_DIR, load_detector, positive_int, probability, project_path, run_name, select_device


def resolve_source(source):
    if str(source) == "webcam":
        return 0
    if str(source).isdigit():
        return int(source)
    path = project_path(source)
    if not path.exists():
        raise FileNotFoundError(f"Input not found: {path}")
    return str(path)


def detection_record(result, sequence_index):
    boxes = []
    if result.boxes is not None:
        coordinates = result.boxes.xyxy.cpu().tolist()
        confidences = result.boxes.conf.cpu().tolist()
        classes = result.boxes.cls.cpu().tolist()
        for coords, confidence, class_id in zip(coordinates, confidences, classes):
            boxes.append({"class_id": int(class_id), "class_name": result.names[int(class_id)],
                          "confidence": float(confidence), "bbox_xyxy": [float(v) for v in coords]})
    return {"source": str(result.path), "sequence_index": sequence_index,
            "image_size": {"height": result.orig_shape[0], "width": result.orig_shape[1]},
            "box_units": "pixels", "detections": boxes}


def detect(source, confidence=0.4, show=False, weights=MODEL_PATH, imgsz=640, device="auto", name="results"):
    confidence = probability(confidence)
    input_source = resolve_source(source)
    model = load_detector(weights)
    device = select_device(device)
    results = model.predict(source=input_source, conf=confidence, imgsz=imgsz,
                            device=device, save=True, show=show, stream=True,
                            project=str(RUNS_DIR / "predictions"), name=run_name(name), exist_ok=False)
    handle = None
    output = None
    frames = 0
    detections = 0
    try:
        for sequence_index, result in enumerate(results):
            if handle is None:
                output = model.predictor.save_dir
                handle = (output / "detections.jsonl").open("w", encoding="utf-8")
            record = detection_record(result, sequence_index)
            handle.write(json.dumps(record, allow_nan=False) + "\n")
            handle.flush()
            frames += 1
            detections += len(record["detections"])
            for box in record["detections"]:
                print(f"POTHOLE DETECTED | confidence={box['confidence']:.3f} | bbox_xyxy={box['bbox_xyxy']}")
    finally:
        results.close()
        if handle:
            handle.close()
        # Ensure video files are playable even when Ctrl+C interrupts streaming.
        if model.predictor:
            for writer in model.predictor.vid_writer.values():
                writer.release()
            dataset = getattr(model.predictor, "dataset", None)
            if hasattr(dataset, "close"):
                dataset.close()
            elif getattr(dataset, "cap", None) is not None:
                dataset.cap.release()
        if show:
            import cv2
            cv2.destroyAllWindows()
    print(f"Processed {frames} images/frames; {detections} detections (not unique potholes).")
    print("Output folder:", output)
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, help="Image, directory, video, webcam, or camera index; paths relative to edge_ai")
    parser.add_argument("--conf", dest="confidence", type=probability, default=0.4)
    parser.add_argument("--show", action="store_true")
    parser.add_argument("--weights", default=str(MODEL_PATH))
    parser.add_argument("--imgsz", type=positive_int, default=640)
    parser.add_argument("--device", default="auto")
    parser.add_argument("--name", type=run_name, default="results")
    args = parser.parse_args()
    try:
        detect(**vars(args))
    except KeyboardInterrupt:
        print("Detection stopped.")
    except (OSError, ValueError) as exc:
        parser.exit(1, f"ERROR: {exc}\n")
