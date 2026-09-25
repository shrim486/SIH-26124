# Pothole detection from car dashcam video

The trained ONNX model detects pothole candidates and draws labeled boxes with confidence scores on every frame of the source video. Outputs preserve the source resolution, frame rate, and duration and use H.264 MP4. Audio is not retained.

## Existing output

Generated videos are local artifacts and are not included in Git. Run the pipeline to create a video under `edge_ai/outputs`. See [asset setup](../docs/ASSETS.md) before running a fresh clone.

This 10-second, 1280×720 video contains 240 processed frames at 24 FPS. The 859 boxes across frames include repeated sightings; they are not a unique pothole count. Misses and false positives remain possible. Green boxes have confidence ≥0.5; amber boxes have lower confidence. Shading fills each rectangle, not a segmentation mask.

## Run from the repository root

```powershell
.venv/Scripts/python.exe -m edge_ai.main --source test_videos/dashcam/candidate.mp4 --output outputs/dashcam_new_run
```

Use a new output directory for each run. Relative source, weights and output paths resolve inside `edge_ai`; absolute paths also work. Supply a forward-facing car dashcam video. The default road crop is calibrated to the included clip; adjust `--road-top` and `--road-bottom` for another camera. The program does not automatically classify camera viewpoints.

Each run writes `potholes_detected.mp4`, per-frame `detections.jsonl`, `summary.json`, and preview frames. If VS Code cannot preview MP4, open it in a browser or your system video player.

## Code and weights

- `main.py`: dashcam command-line entry point.
- `detectors/road_hazards/pothole_detector.py`: ONNX inference, overlapping crops and duplicate suppression.
- `processing/frame_processor.py`: annotations, video encoding and detection records.
- `cameras/camera_manager.py`: video metadata and capture handling.
- `training/`: dataset validation/import, training, evaluation and export.
- `models/road_hazards/pothole/best.onnx`: selected public pothole model.
- `models/pretrained/yolov8n.pt`: generic starting weights for training, not a trained pothole detector.
- `tests/`: pipeline and detector checks.

The selected model comes from [subhodeepmoitra/pothole-detection-yolov8](https://huggingface.co/subhodeepmoitra/pothole-detection-yolov8). The input is the [Rajarshisaha10 dashcam sample](https://github.com/Rajarshisaha10/Pothole_detection_YOLO/blob/main/assets/sample_video_before.mp4). Reference asset hashes and provenance are recorded in [docs/assets.json](../docs/assets.json).

There is no locally trained pothole `best.pt` yet. Training requires a real labeled dataset. Run `python -m edge_ai.training.train --help` for options; use the same module style for `check_dataset`, `import_dataset`, `evaluate`, and `export_model`.

Dependencies: `.venv/Scripts/python.exe -m pip install -r edge_ai/requirements-video-demo.txt` from the project folder.

Checks: `.venv/Scripts/python.exe -m unittest discover -s edge_ai/tests -p "test_*.py"`.
