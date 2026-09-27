# Waterlogging Edge AI

This module detects waterlogging from a recorded bus-camera video using a YOLO model.

## Pipeline

Video -> YOLO detection -> confidence filtering -> multi-frame validation -> simulated GPS -> backend alert

## Model

The prototype's trained YOLO weights (`best.pt`) are included in Git at the path below. Larger suite weights use the separate asset release.

Expected local model path:

models/best.pt

## Demo video

The recorded input and annotated output video are included in the source repository.

Expected local video path:

videos/waterlogging.mp4

## Backend endpoint

POST /api/v1/events/ingest

The client authenticates using `GOVERNMENT_USERNAME` and `GOVERNMENT_PASSWORD`
from the process environment or the local `backend/.env` created by setup.
It refreshes an expired session once and never prints the credentials/token.
It does not claim a registered bus or camera identity for this recorded footage.

## Event

The module generates validated waterlogging events containing confidence, timestamp, latitude, longitude, severity, bus ID, and status.

GPS is simulated for the prototype.
