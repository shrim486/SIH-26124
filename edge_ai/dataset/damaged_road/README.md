# Damaged-road dataset

This dataset belongs to the damaged-road model, not the pothole model.

Expected YOLO layout:

```text
damaged_road/
├── data.yaml
├── train/images/
├── train/labels/
├── valid/images/
├── valid/labels/
├── test/images/
└── test/labels/
```

This is a single-class model. D00 longitudinal cracks, D10 transverse cracks,
D20 alligator cracks, and labelled deteriorated surfaces map to `damaged_road`.
D40 potholes are intentionally excluded because Model 1 handles potholes.

Place the RDD2022 India archive under `raw/rdd2022_india/`, then run:

```powershell
python -m edge_ai.training.prepare_damaged_road
python -m edge_ai.training.check_damaged_road
```

To build local annotation material from the dashcam video only:

```powershell
python -m edge_ai.training.extract_damaged_road_frames
```

This extracts spaced frames under `raw/dashcam_frames/`. Manually annotate
cracks and deteriorated asphalt as class `0` and create matching YOLO label
files before copying those images into a train, valid, or test split.
