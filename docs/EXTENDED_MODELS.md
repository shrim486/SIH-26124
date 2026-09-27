# Extended model pipeline

## Run

From the repository root, after installing `requirements.txt`:

```powershell
python scripts/fetch_extended_models.py
python -m edge_ai.suite --source edge_ai/test_videos/dashcam/candidate.mp4
```

Use your configured virtual environment's Python. The original workspace uses `../.venv/Scripts/python.exe`. An example with selected tasks:

```powershell
python -m edge_ai.suite --source your_dashcam.mp4 --tasks pothole damaged_road zebra_crossing number_plate helmet triple_riding
```

Every decoded frame is processed. Output folders contain H.264 `annotated.mp4`, `preview.jpg`, `detections.jsonl`, and `summary.json`. `--max-frames 24` creates an explicitly truncated development check. Existing output directories are refused. CPU processing is significantly slower than playback when all models are selected.

Use `--road-bottom 0.68` for the supplied dashcam, whose dashboard begins around 68% of image height. This removes predictions centered inside the dashboard, including observed false crosswalk/car boxes. The default is 1.0 (full image); calibrate it for each camera. The portal exposes the same setting as a percentage. Accident confidence is 0.60 after a low-confidence parked-car false positive was observed. These are development adjustments, not proof of improved general accuracy.

Saved predictions can be re-rendered without repeating inference:

```powershell
python scripts/render_detections.py --run edge_ai/outputs/extended_suite_full --output edge_ai/outputs/extended_suite_reviewed --road-bottom 0.68
```

This preserves the original run and input, records applied filters, and cannot add missed detections. Road-region filtering changes displayed boxes; traffic motion measurements still use their configured zones.

The citizen portal's government dashboard has Video Analysis profiles for road hazards, motorcycles, number plates, possible accident scenes, fixed-camera queues, and all visual models. The API defaults to local inference without a Roboflow key. The standalone motorcycle command retains optional `--provider roboflow`; install its optional requirements and configure the key in the process environment to use that provider.

## What each implementation means

| Task | Implementation | Validation boundary |
| --- | --- | --- |
| Pothole | Existing pothole ONNX | Previously checked on full dashcam; no general accuracy claim |
| Damaged road | Existing RDD checkpoint | Cracks only; existing class filtering preserved |
| Waterlogging | YOLO-World prompts for puddles/flooded road | Experimental zero-shot candidates, not a validated flood detector or water-depth estimate |
| Road divider | YOLO-World prompts for median/barriers/guardrails | Experimental broad barrier candidates; no segmentation or geometry guarantee |
| Zebra crossing | Author's supervised YOLOv8m crosswalk model | Small upstream held-out subset checked; not India-specific validation |
| Traffic sign | YOLO-World broad sign localization | Experimental; does not read or classify all sign meanings |
| Accident | Public accident-evaluator checkpoint | Visual candidates from publisher's high/medium/low labels; no confirmed crash, injury diagnosis, causality, or emergency dispatch |
| Plate/OCR | FastALPR ONNX detector plus CCT OCR | Local OCR; must be tested for local plate scripts/layouts; no owner lookup |
| Helmet | Local YOLOv8n helmet/no-helmet checkpoint | Associated with motorcycle tracks; best head per motorcycle, not full passenger compliance |
| Triple riding | Learned person/motorcycle detections plus geometric/temporal rules | Possible violation; overlap and occlusion can cause errors; not a separately trained classifier |
| Congestion | Persistent counts and slow tracked motion | Fixed-camera rule candidate; not calibrated km/h or a trained congestion model |
| Bottleneck | Persistent upstream queue with downstream movement | Requires meaningful user-defined zones; cannot establish road-network causality |

The main road models and source videos still need the separate assets described in [ASSETS.md](ASSETS.md). Extended checkpoint URLs, sizes, and SHA-256 hashes are in [extended-model-assets.json](extended-model-assets.json). No downloaded binary is automatically published.

## Fixed-camera traffic

```powershell
python -m edge_ai.suite --source fixed_camera.mp4 --camera fixed --tasks congestion bottleneck --zones edge_ai/config/traffic_zones.example.json
```

Replace the example normalized rectangles with the actual upstream/downstream areas of your camera, in flow order. Defaults require at least five measured vehicles, a 60% slow fraction, and a three-second persistent queue. Speed is in vehicle-heights per second, not physical speed. Moving dashcam input is explicitly rejected for these tasks. No fixed-camera validation video has been supplied, so rule tests are not field validation.

## Datasets and training

```powershell
python scripts/fetch_dataset_samples.py --per-split 12
python -m edge_ai.training.manage_dataset check --data edge_ai/dataset/traffic_sign/data.yaml
python -m edge_ai.training.manage_dataset check --data edge_ai/dataset/zebra_crossing/data.yaml
python scripts/evaluate_extended_samples.py
```

`--resume` preserves matching downloaded files and rejects local modifications. The importer retains upstream train/validation/test splits, deduplicates image bytes, and keeps one original crosswalk photo group rather than several augmented copies. Each sample subset has 12 images per split. Traffic signs are explicitly mapped from 43 sign types to the single localization class; original categories stay in `provenance.json`. These are small development subsets, not production training sets.

The validator checks class IDs, finite boxes, image bounds, missing labels, empty splits, and identical decoded images across splits. Do not treat absent labels as negative examples. A real training command after supplying sufficient labeled data:

```powershell
python -m edge_ai.training.manage_dataset train --data path/to/data.yaml --weights edge_ai/models/pretrained/yolov8n.pt --output edge_ai/outputs/my_training --epochs 50
```

Training never overwrites inference weights. Evaluation requires an exact dataset/model class-name match. Positive image demos of helmet, accident and plate inference have no independent bounding-box ground truth; do not report them as accuracy tests.

## Data sources and remaining acquisition

- [Traffic-sign labeled data](https://huggingface.co/datasets/keremberke/german-traffic-sign-detection): small subsets downloaded locally. German signs do not establish Indian road performance.
- [Crosswalk model and labeled data](https://github.com/piranha9827/Crosswalks-Detection-using-YOLO): pinned revision, GPL-3.0 as stated by the publisher.
- [Helmet checkpoint](https://huggingface.co/iam-tsr/yolov8n-helmet-detection): publisher labels helmet/no_helmet. [Helmet scene samples](https://huggingface.co/datasets/pzalavad/HelmetDataset) have image-level labels only and cannot train a box detector as-is.
- [Accident checkpoint](https://huggingface.co/Enos-123/accident-evaluator-yolov8x): publisher demo images checked separately. [Car Crash Dataset](https://github.com/Cogito2012/CarCrashDataset) is a source for temporal dashcam validation, not yet imported.
- [UW-Bench](https://github.com/zhang-chenxu/LSM-Adapter): access agreement and publisher password required. No agreement was submitted and this dataset is not downloaded.
- [Mapillary training datasets](https://ai.meta.com/ai-for-good/datasets/mapillary-training-datasets/): source for divider/barrier/crosswalk annotations under publisher access terms. Not downloaded; no dedicated divider training claimed.
- [FastALPR](https://github.com/ankandrew/fast-alpr): installs/downloads its detector and OCR assets locally under `edge_ai/models/number_plate`.
- [YOLO-World](https://docs.ultralytics.com/models/yolo-world/): pretrained open-vocabulary baseline. Text embeddings are cached locally to avoid repeatedly loading the CLIP encoder.

Review source licenses before redistributing data/checkpoints. Local validation and fine-tuning on sufficient Indian road footage remain necessary for dependable deployment.

## Local checks on 2026-09-26

- Crosswalk: 12 test images, 18 matched boxes, 0 false positives, 0 misses at IoU 0.5. This small upstream subset does not establish general accuracy or independence from checkpoint training data.
- Traffic signs, default YOLO-World: 12 test images, 4 matches, 9 false positives, 9 misses (30.8% precision/recall). This is weak and remains experimental.
- An optional [21-category supervised checkpoint](https://huggingface.co/yahyagul/traffic-sign-yolov8) is available with `--sign-backend supervised`. Traffic-light classes are filtered. It had 1 match, 0 false positives and 12 misses on the German-sign subset, so it is not the default. Its narrower category set does not cover every German sign.
- Plate/OCR: the public demo image produced one correctly localized plate and text `5AU5341`. This is a functional check, not an OCR benchmark.
- Accident: three publisher example images produced four candidate boxes. These are publisher demos, not independent validation.
- Helmet: one detection across six unannotated sample images; several samples are isolated product photos. No reliable helmet/no-helmet recall estimate is available.
- The two downloaded datasets contain 72 images total across preserved train/validation/test splits. Images and labels stay ignored by Git; configs/provenance are shareable. No model has been newly trained on this subset.
- Congestion/bottleneck and rider rules have unit checks, but still lack annotated real-video validation. Waterlogging and divider prompts lack labeled local evaluation data.

Detailed local output: `edge_ai/outputs/extended_evaluation/report.json` and `supervised_sign_report.json`; visual checks are beside them. The upload API was also exercised with an actual three-frame dashcam clip and returned a decodable MP4 with matching dimensions/FPS/frame count.

## Completed video and software checks

The full ten-model dashcam run processed 240/240 frames (1280x720, 24 FPS, 10 seconds). The reviewed output is `edge_ai/outputs/extended_suite_reviewed/annotated.mp4`. All 240 frames were decoded again, H.264/yuv420p encoding was verified, and the source SHA-256 remained unchanged. `verification.json`, `summary.json` and per-frame predictions are beside the video. The source clip does not contain positive examples of every supported task.

The original unfiltered inference run remains in `edge_ai/outputs/extended_suite_full`. It took 1775 seconds (about 29.6 minutes) on this CPU while other checks were running. This combined setup is not real-time. Select only needed tasks for shorter turnaround.

25 AI unit tests and 3 backend tests passed. The updated citizen portal built successfully; lint reports existing unrelated warnings. Live API uploads were checked for both plate OCR and the six-model road profile, including the dashboard exclusion setting. The standalone offline motorcycle CLI also encoded a three-frame check successfully. These software checks are separate from model-accuracy validation.
