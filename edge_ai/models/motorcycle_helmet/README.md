# Motorcycle and helmet detection

This pipeline combines a YOLO vehicle model with the Roboflow helmet model from the supplied notebook. It accepts a local video instead of the Google Colab upload widget and writes an annotated MP4, per-frame JSONL detections, and a summary.

Install from the repository root:

```bash
python3 -m pip install -r edge_ai/requirements-motorcycle-helmet.txt
```

Run with the API key in the environment:

```bash
export ROBOFLOW_API_KEY="your-key"
python3 -m edge_ai.models.motorcycle_helmet.detect --source /path/to/video.mp4
```

The script prompts securely for the key when `ROBOFLOW_API_KEY` is not set. The first run downloads the configured vehicle weights. Results are written to `edge_ai/outputs/motorcycle_helmet` by default. Audio is not retained in the OpenCV output.