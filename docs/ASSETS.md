# Model and video assets

Saved videos, detected images and model weights are available in versioned GitHub release bundles. `python scripts/setup.py` restores portal evidence and map records; add `--with-models --with-originals` for model weights and full inputs. See [shared video setup](SHARED_VIDEOS.md). Binary assets are ignored in source commits. [release-assets.json](release-assets.json) pins each archive checksum, and [assets.json](assets.json) records the original tested pothole/road-model files.

| Asset | Required location | Source |
| --- | --- | --- |
| Pothole ONNX | `edge_ai/models/road_hazards/pothole/best.onnx` | [Public checkpoint](https://huggingface.co/subhodeepmoitra/pothole-detection-yolov8/tree/f829c25ade58a613e4a54ccc3c9759fc82b9e292), file `best.onnx` |
| Damaged-road checkpoint | `edge_ai/models/road_hazards/damaged_road/best.pt` | Existing locally supplied RDD checkpoint; original download URL was not recorded |
| Reference car dashcam | `edge_ai/test_videos/dashcam/candidate.mp4` | [sample_video_before.mp4](https://github.com/Rajarshisaha10/Pothole_detection_YOLO/blob/main/assets/sample_video_before.mp4) |

Download from the respective publisher, create destination directories, and copy files into those locations. Run `python scripts/check_assets.py` to verify them. Use only trusted checkpoints. Another damaged-road checkpoint must expose `D00`, `D10`, `D20` or `damaged_road` classes and needs its own recorded provenance and verification hash.

The optional model bundle contains the locally supplied damaged-road checkpoint; its original download URL was not recorded. Third-party redistribution terms have not been independently established here. Download availability is not a new license grant; retain publisher attribution and review original terms for your intended use. Default setup downloads saved evidence; `--with-models` additionally downloads model binaries.

For pothole-only inference, only its model and a video are required:

```powershell
.venv/Scripts/python.exe -m edge_ai.main --source test_videos/dashcam/candidate.mp4 --output outputs/my_pothole_run
```

Use a fresh output directory. Adjust `--road-top` and `--road-bottom` for another camera. Output is annotated video, not ground-truth labels or a unique pothole count.

Training requires labeled image/label splits; see the dataset READMEs. Optional generic `edge_ai/models/pretrained/yolov8n.pt` initializes training and is not the pothole inference checkpoint.
