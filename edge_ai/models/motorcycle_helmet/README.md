# Motorcycle and helmet detection

This pipeline combines local YOLO vehicle tracking with a helmet/no-helmet checkpoint. It writes an annotated H.264 MP4, per-frame JSONL detections, and a summary. Rider alerts use geometric and temporal rules and need human review.

Install from the repository root:

```bash
python3 -m pip install -r edge_ai/requirements-extended.txt
python3 scripts/fetch_extended_models.py --models helmet
```

Run offline:

```bash
python3 -m edge_ai.models.motorcycle_helmet.detect --source /path/to/video.mp4
```

The default provider needs no API key. Vehicle weights must be present at `edge_ai/models/motorcycle_helmet/yolo26n.pt`. Results are written to `edge_ai/outputs/motorcycle_helmet` by default. Encoding uses FFmpeg from PATH or imageio-ffmpeg; audio is omitted.

For optional cloud compatibility, install `requirements-motorcycle-helmet.txt`, set `ROBOFLOW_API_KEY` locally and pass `--provider roboflow`. No key is requested interactively. The unified runner also accepts `--tasks helmet triple_riding`; see [extended model validation](../../../docs/EXTENDED_MODELS.md).

For a combined helmet/plate video, run the unified suite with `--tasks helmet number_plate`.
The `slow_riders` demonstration in `scripts/run_demo_videos.py` uses a 16-second
on-bike excerpt containing helmeted riders and bare-headed passengers. See
[portal demonstrations](../../../docs/PORTAL_VERIFICATION.md) for measured frame
counts, source attribution, and map links. A majority of recent predictions
must agree with the current head class before a box is emitted; history cannot
relabel the current box. One head is selected per motorcycle, so multi-rider
recall remains limited. OCR text and predicted helmet status need review.
