from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import cv2
import matplotlib
import numpy as np

matplotlib.use("Agg")

import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch


ROOT = Path(__file__).resolve().parent.parent
ASSETS = Path(__file__).resolve().parent
OUTPUTS = ROOT / "edge_ai" / "outputs"

INK = "#172b4d"
BLUE = "#2463a6"
TEAL = "#168c83"
PALE_BLUE = "#eaf2fb"
PALE_TEAL = "#e7f5f2"
GRAY = "#65758b"
ORANGE = "#e59b30"
RED = "#c65b55"


def draw_box(ax, xy, width, height, label, facecolor, edgecolor=BLUE, fontsize=12):
    x, y = xy
    patch = FancyBboxPatch(
        (x, y),
        width,
        height,
        boxstyle="round,pad=0.02,rounding_size=0.04",
        linewidth=1.6,
        edgecolor=edgecolor,
        facecolor=facecolor,
    )
    ax.add_patch(patch)
    ax.text(
        x + width / 2,
        y + height / 2,
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=INK,
        fontweight="semibold",
        linespacing=1.35,
    )


def draw_arrow(ax, start, end, color=GRAY, rad=0):
    ax.add_patch(
        FancyArrowPatch(
            start,
            end,
            arrowstyle="-|>",
            mutation_scale=15,
            linewidth=1.5,
            color=color,
            connectionstyle=f"arc3,rad={rad}",
        )
    )


def architecture_figure():
    fig, ax = plt.subplots(figsize=(13.8, 5.3))
    ax.set_xlim(0, 13.8)
    ax.set_ylim(0, 5.3)
    ax.axis("off")
    ax.set_title(
        "AI-Powered Mobile Urban Intelligence Platform",
        fontsize=18,
        fontweight="bold",
        color=INK,
        pad=18,
    )

    draw_box(ax, (0.25, 2.25), 2.1, 1.25, "Video sources\nDashcam\nRoadside camera", PALE_BLUE, fontsize=10.5)
    draw_box(ax, (2.9, 2.05), 2.5, 1.65, "On-device edge AI\n12 detection types\nVideo + JSONL evidence", PALE_TEAL, TEAL, 10.5)
    draw_box(ax, (5.95, 2.05), 2.3, 1.65, "FastAPI services\nEvent ingestion\nSQLite + audit history", PALE_BLUE, fontsize=10.5)
    draw_box(ax, (8.8, 3.4), 2.25, 1.2, "Citizen portal\nMap | Alerts | Routing", PALE_TEAL, TEAL, 10.5)
    draw_box(ax, (8.8, 1.05), 2.25, 1.35, "Government portal\nCases | Evidence | Fleet", PALE_BLUE, fontsize=10.5)
    draw_box(ax, (11.55, 1.9), 2.0, 1.7, "Public transport\nFleet monitoring\nGPS | Camera health", "#fff4df", ORANGE, 9.5)

    draw_arrow(ax, (2.35, 2.88), (2.9, 2.88))
    draw_arrow(ax, (5.4, 2.88), (5.95, 2.88))
    draw_arrow(ax, (8.25, 2.98), (8.8, 3.92), rad=-0.08)
    draw_arrow(ax, (8.25, 2.65), (8.8, 1.75), rad=0.08)
    draw_arrow(ax, (11.05, 1.72), (11.55, 2.25))

    ax.text(0.3, 0.55, "Local-first processing; media access is restricted by role.", fontsize=10, color=GRAY)
    fig.tight_layout()
    fig.savefig(ASSETS / "fig1_architecture.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def pipeline_figure():
    fig, ax = plt.subplots(figsize=(13.8, 4.6))
    ax.set_xlim(0, 13.8)
    ax.set_ylim(0, 4.6)
    ax.axis("off")
    ax.set_title("Video-to-Incident Processing Pipeline", fontsize=18, fontweight="bold", color=INK, pad=18)

    nodes = [
        ("1. Capture", "Read video frame\nand metadata", PALE_BLUE, BLUE),
        ("2. Prepare", "Crop road ROI\nnormalize frame", PALE_TEAL, TEAL),
        ("3. Detect", "Run selected\nlocal models", PALE_BLUE, BLUE),
        ("4. Track + filter", "NMS, confidence,\ntemporal rules", "#fff4df", ORANGE),
        ("5. Publish", "Encode H.264\nwrite JSONL", PALE_TEAL, TEAL),
        ("6. Manage", "Create shared case\nand update portals", PALE_BLUE, BLUE),
    ]
    positions = [0.15, 2.45, 4.75, 7.05, 9.35, 11.65]
    for x, (title, desc, facecolor, edgecolor) in zip(positions, nodes):
        draw_box(ax, (x, 1.55), 1.95, 1.45, f"{title}\n{desc}", facecolor, edgecolor, 10.5)
    for x1, x2 in zip(positions[:-1], positions[1:]):
        draw_arrow(ax, (x1 + 1.95, 2.27), (x2, 2.27))
    ax.text(0.2, 0.65, "Per-frame outputs: annotated evidence, timestamps, detector labels, confidence scores, and event metadata.", fontsize=10, color=GRAY)
    fig.tight_layout()
    fig.savefig(ASSETS / "fig2_pipeline.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def coverage_figure():
    detections_path = OUTPUTS / "extended_suite_reviewed" / "detections.jsonl"
    counts = Counter()
    frame_count = 0
    with detections_path.open(encoding="utf-8") as detection_file:
        for line in detection_file:
            frame = json.loads(line)
            frame_count += 1
            for detection in frame.get("detections") or []:
                category = detection.get("detector") or detection.get("class_name") or detection.get("label")
                if category:
                    counts[category] += 1

    category_names = {
        "pothole": "Pothole",
        "damaged_road": "Road damage",
        "car": "Car",
        "road_scene": "Road-scene candidate",
    }
    categories = [
        (category_names[key], count)
        for key, count in counts.most_common()
        if key in category_names
    ]
    labels = [label for label, _ in categories]
    values = [count for _, count in categories]

    fig, ax = plt.subplots(figsize=(10.8, 4.6))
    y_positions = list(range(len(labels)))
    bars = ax.barh(y_positions, values, color=[TEAL, BLUE, ORANGE, RED][: len(values)], height=0.62)
    ax.set_yticks(y_positions, labels, fontsize=10)
    ax.invert_yaxis()
    ax.set_xlim(0, max(values, default=1) * 1.2)
    ax.set_xlabel("Per-frame bounding-box observations", fontsize=9, color=GRAY, labelpad=8)
    ax.tick_params(axis="x", labelsize=9, colors=GRAY)
    ax.tick_params(axis="y", length=0, pad=10)
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.grid(axis="x", color="#e2e7ed", linewidth=0.8)
    ax.set_axisbelow(True)
    for bar, value in zip(bars, values):
        ax.text(value + max(values) * 0.015, bar.get_y() + bar.get_height() / 2, f"{value:,}", va="center", fontsize=9, color=INK)
    ax.set_title(
        f"Saved detector output | {frame_count} analyzed frames",
        fontsize=16,
        color=INK,
        fontweight="bold",
        pad=15,
    )
    fig.text(
        0.5,
        0.015,
        "Repeated per-frame observations from detections.jsonl; not unique incidents or accuracy scores.",
        ha="center",
        fontsize=9,
        color=GRAY,
    )
    fig.tight_layout(rect=(0, 0.1, 1, 0.94))
    fig.savefig(ASSETS / "fig3_detection_coverage.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def frame_at(path: Path, seconds: float):
    capture = cv2.VideoCapture(str(path))
    if not capture.isOpened():
        raise RuntimeError(f"Could not open video: {path}")
    fps = capture.get(cv2.CAP_PROP_FPS)
    frame_count = int(capture.get(cv2.CAP_PROP_FRAME_COUNT))
    index = min(max(round(fps * seconds), 0), frame_count - 1)
    capture.set(cv2.CAP_PROP_POS_FRAMES, index)
    ok, frame = capture.read()
    capture.release()
    if not ok or frame is None:
        raise RuntimeError(f"Could not read frame {index} from: {path}")
    return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)


def crop_letterbox(image):
    non_white = (image.min(axis=2) < 242) | (image.max(axis=2) - image.min(axis=2) > 12)
    rows, columns = non_white.nonzero()
    if len(rows) == 0:
        return image
    top, bottom = max(0, rows.min() - 8), min(image.shape[0], rows.max() + 9)
    left, right = max(0, columns.min() - 8), min(image.shape[1], columns.max() + 9)
    return image[top:bottom, left:right]


def evidence_figure():
    examples = [
        (
            "Provided waterlogging video | source frame",
            ROOT / "videos" / "waterlogging.mp4",
            2.0,
            "source",
        ),
        (
            "Waterlogging model output | candidate",
            ROOT / "videos" / "waterlogging_ai_output.mp4",
            2.0,
            "output",
        ),
        (
            "Pothole detection | dashcam",
            OUTPUTS / "dashcam_more_sensitive" / "potholes_detected.mp4",
            3.0,
            "output",
        ),
        (
            "Accident detection | demo clip",
            OUTPUTS / "bengaluru_accident_demo" / "annotated.mp4",
            3.0,
            "output",
        ),
        (
            "Rider detection | demo clip",
            OUTPUTS / "demo_triple_riders" / "annotated.mp4",
            3.0,
            "output",
        ),
    ]
    fig = plt.figure(figsize=(15, 6.6))
    grid = fig.add_gridspec(2, 6, height_ratios=[1.0, 1.0], hspace=0.03, wspace=0.08)
    axes = [
        fig.add_subplot(grid[0, :3]),
        fig.add_subplot(grid[0, 3:]),
        fig.add_subplot(grid[1, :2]),
        fig.add_subplot(grid[1, 2:4]),
        fig.add_subplot(grid[1, 4:]),
    ]
    for ax, (label, path, seconds, kind) in zip(axes, examples):
        image = crop_letterbox(frame_at(path, seconds))
        ax.imshow(image)
        ax.set_title(label, fontsize=10.5, color=INK, fontweight="semibold", loc="left", pad=7)
        ax.axis("off")
        ax.text(
            0.01,
            0.02,
            "Original video" if kind == "source" else f"Annotated output | t = {seconds:.1f} s",
            transform=ax.transAxes,
            fontsize=8,
            color="white",
            bbox={"facecolor": INK, "alpha": 0.78, "pad": 3, "edgecolor": "none"},
        )
    fig.suptitle("Selected video frames and saved model detections", fontsize=18, color=INK, fontweight="bold", y=0.99)
    fig.text(
        0.5,
        0.015,
        "Examples are detector candidates from the supplied clips and saved project outputs; they do not represent measured model accuracy.",
        ha="center",
        fontsize=9,
        color=GRAY,
    )
    fig.savefig(ASSETS / "fig4_video_evidence.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def supplied_screenshots_figure():
    examples = [
        ("Public-transport traffic scene", "fleet-traffic.png"),
        ("Motorcycle, helmet and plate candidates", "helmet-plate-detection.png"),
        ("Road damage and waterlogging candidates", "road-damage-detections.png"),
        ("Accident candidate", "accident-candidate.png"),
        ("Government operations dashboard", "government-dashboard.png"),
        ("Citizen road-condition map", "citizen-road-map.png"),
    ]
    fig, axes = plt.subplots(2, 3, figsize=(15, 7.5))
    for ax, (caption, filename) in zip(axes.flat, examples):
        image = np.asarray(plt.imread(ASSETS / filename))
        if image.dtype != np.uint8:
            image = np.clip(image * 255, 0, 255).astype(np.uint8)
        height, width = image.shape[:2]
        scale = min(1600 / width, 900 / height)
        resized = cv2.resize(image, (round(width * scale), round(height * scale)), interpolation=cv2.INTER_AREA)
        fitted = np.full((900, 1600, 3), 255, dtype=np.uint8)
        if resized.ndim == 2:
            resized = cv2.cvtColor(resized, cv2.COLOR_GRAY2RGB)
        elif resized.shape[2] == 4:
            resized = cv2.cvtColor(resized, cv2.COLOR_RGBA2RGB)
        top = (900 - resized.shape[0]) // 2
        left = (1600 - resized.shape[1]) // 2
        fitted[top : top + resized.shape[0], left : left + resized.shape[1]] = resized[:, :, :3]
        ax.imshow(fitted)
        ax.set_title(caption, fontsize=9.5, color=INK, fontweight="semibold", loc="left", pad=6)
        ax.axis("off")
    fig.suptitle("Selected project footage and portal screenshots", fontsize=16, color=INK, fontweight="bold", y=0.99)
    fig.text(
        0.5,
        0.015,
        "User-provided examples. Detector boxes are model candidates; the portal values are a point-in-time screenshot.",
        ha="center",
        fontsize=8.5,
        color=GRAY,
    )
    fig.subplots_adjust(left=0.035, right=0.985, top=0.9, bottom=0.1, hspace=0.15, wspace=0.08)
    fig.savefig(ASSETS / "fig5_supplied_project_screenshots.png", dpi=220, bbox_inches="tight", facecolor="white")
    plt.close(fig)


def main():
    ASSETS.mkdir(parents=True, exist_ok=True)
    architecture_figure()
    pipeline_figure()
    coverage_figure()
    evidence_figure()
    supplied_screenshots_figure()
    print(f"Generated report figures in {ASSETS}")


if __name__ == "__main__":
    main()
