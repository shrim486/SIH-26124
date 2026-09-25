# Dataset

Download the **YOLOv8 object detection** ZIP from
[Roboflow's public pothole dataset](https://public.roboflow.com/object-detection/pothole/1/download/yolov8).
The source credits Atikur Rahman Chitholian, lists 665 annotated images and ODbL v1.0,
and describes a 70/20/10 train/validation/test split. Verify the counts after export.

Run from the project root using the actual ZIP path:

```powershell
.\.venv\Scripts\python.exe pothole_detection/import_dataset.py "C:\Users\diksh\Downloads\pothole.zip"
```

The importer preserves split assignments, checks the original class metadata,
and keeps the original YAML and source README files. It accepts `pothole` or
`potholes` as the single class without renaming it. It rejects classification,
segmentation and multi-class exports. It validates images and labels before copying.

For manual extraction, place `train`, `valid` (or `val`), `test` and `data.yaml`
directly in this directory. Update the `val:` entry if needed. The scripts resolve
relative paths against the YAML's directory and save a resolved YAML with each run.
Do not leave an absolute `path:` referring to someone else's computer.

Missing annotation files fail validation to require human review. For a verified
pothole-free image, supply an empty `.txt` file with the same stem. Incorrectly
annotated negatives would teach the model to ignore real potholes.

Keep footage from the same recording or road segment in one split. The checker
detects exact decoded-image duplicates across splits, not every near duplicate.
