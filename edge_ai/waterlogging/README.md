# Waterlogging Edge AI

This module detects waterlogging from a recorded bus-camera video using a YOLO model.

## Pipeline

Video -> YOLO detection -> confidence filtering -> multi-frame validation -> simulated GPS -> backend alert

## Model

The trained YOLO weights (`best.pt`) are stored outside Git because model binaries are excluded by the repository `.gitignore`.

Expected local model path:

models/best.pt

## Demo video

The recorded demo video is also kept outside the source repository.

Expected local video path:

videos/waterlogging.mp4

## Backend endpoint

POST /api/v1/events/ingest

## Event

The module generates validated waterlogging events containing confidence, timestamp, latitude, longitude, severity, bus ID, and status.

GPS is simulated for the prototype.
