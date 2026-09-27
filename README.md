# AI-Powered Urban Intelligence

FastAPI backend, React citizen and government portals, and local machine-learning video analysis with annotated H.264 output.

## Current capabilities

- Pothole ONNX inference: overlapping road crops, confidence-labeled boxes, H.264 MP4 and per-frame JSONL.
- Damaged-road inference: separate RDD checkpoint filtering longitudinal, transverse and alligator cracks.
- Extended video pipeline: crosswalks, experimental waterlogging/dividers/signs, accident candidates, plate OCR, offline helmets and rider counting.
- Fixed-camera congestion and bottleneck candidates from vehicle tracking and temporal rules.
- Backend: event ingestion, duplicate handling, government authentication, road issues, alerts and dashboards.
- Portals: citizen reporting/maps, route planning with ordered stops, and government dashboards.
- Shared incident records keep map pins, active-alert counts and recorded evidence aligned across both portals. Fleet monitoring includes GPS history and reported camera health; see [portal and fleet guide](docs/FLEET_AND_PORTAL_RECORDS.md).
- Fleet monitoring also supports protected live camera previews from an RTSP/HTTP/USB edge connector, with optional pothole boxes. See [camera connection setup](docs/LIVE_CAMERAS.md). A physical camera/feed must be connected before any live footage appears.
- Government pages verify the session with the API; evidence, camera previews and video analysis require government credentials. See [access controls and verification](docs/GOVERNMENT_ACCESS.md).

AI inference runs locally after asset setup. Reviewed detections can be published with supplied coordinates; continuous camera GPS ingestion and live traffic estimates require connected data sources. Model quality varies: see [implementation and validation status](docs/EXTENDED_MODELS.md). Dataset download/check/train/evaluate commands are included; downloaded data stays outside Git.

## Setup after cloning

Use Python 3.10 (tested), Node.js 22.12+ and npm. Run commands from this repository root:

```powershell
python scripts/setup.py
```

This creates `.venv`, installs Python dependencies and both portals with `npm ci`, and creates missing `.env` files without replacing existing configuration. It also downloads the saved videos and detected images, verifies their checksums, and restores five linked map alerts into an empty database. This works after **git clone or Download ZIP**. Government credentials and a generated signing secret are in `backend/.env`; keep that file private. For configuration only: `python scripts/setup.py --config-only`.

For all model weights and full original videos, use `python scripts/setup.py --with-models --with-originals`. To install without media, use `--skip-assets`. See [shared videos and download instructions](docs/SHARED_VIDEOS.md), including manual download links and existing-installation behavior. The asset release is public; downloaded footage is not protected by the portal login.

Environment variable names are documented in each component's `.env.example`. Variables prefixed `VITE_` are public frontend configuration, never secrets.

## Start the applications

Windows:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File ./start.ps1
```

| Service | Local address |
| --- | --- |
| Citizen portal | http://127.0.0.1:5173 |
| Government portal | http://127.0.0.1:5174 |
| API documentation | http://127.0.0.1:8000/docs |

Logs/PIDs are under `.runtime`. The launcher leaves occupied ports alone and prefers this repository's `.venv`, with a fallback to the original workspace environment. Stop a launched service with `Stop-Process -Id <PID>`.

macOS/Linux: open three terminals from the repository root and run one command in each:

```sh
(cd backend && ../.venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000)
(cd user_portal && npm run dev -- --host 127.0.0.1 --port 5173 --strictPort)
(cd government_portal && npm run dev -- --host 127.0.0.1 --port 5174 --strictPort)
```

SQLite tables are created at API startup. Government login uses the credentials in local `backend/.env`. These are local development instructions, not production deployment configuration.

Citizen **[Plan Route](http://127.0.0.1:5173/plan-route)** compares road-network alternatives using active accident, waterlogging, road-damage and traffic reports. Enter pickup/drop-off, add up to three ordered stops, and choose a balance between estimated driving time and reported hazards. Assigned map positions are excluded unless explicitly selected. See [routing setup and limits](docs/ROUTE_PLANNER.md).

Government cases are available at [Detected Issues Map](http://127.0.0.1:5174/detections), with separate road, accident and violation pages. Each issue and government alert displays its annotated video and detected images. The [Videos & Images](http://127.0.0.1:5174/ai-results) menu collects evidence for actionable map issues. Resolve or reopen a case to update its citizen alert. Saved analyses remain available through the analysis API and the existing citizen **Video Analysis** tools. See [government operations and fleet setup](docs/GOVERNMENT_OPERATIONS.md).

To publish any supported detection, review its detected segment and fill in the location and time under **Detection map reports**. Publication creates one record shared by the [user map](http://127.0.0.1:5173/map) and [government Detected Issues Map](http://127.0.0.1:5174/detections). **Video and detected frames** opens the matching annotated video and frames containing that prediction, including associated rider/plate frames when available. Repeating the same publication does not create duplicate markers. Media requires government authentication.

Use **Location and time assigned for visualization** when placing footage without verified GPS or recording time. The portals show the location source and assigned time. The included footage uses assigned Bengaluru map locations and times; original recording details are in [source provenance](docs/accident-demo-source.json). Source videos and generated outputs are distributed separately in the [asset release](docs/SHARED_VIDEOS.md).

Alerts are available on the [citizen map](http://127.0.0.1:5173/alerts) and
[government map](http://127.0.0.1:5174/alerts). Published major hazards and
no-helmet candidates create linked alerts; helmet analysis includes plate/OCR.
Government users can inspect same-motorcycle plate candidates and video frames,
and dismiss/reactivate alerts. Real GPS comes from camera telemetry or supplied
incident coordinates; sample locations and times are assigned. See
[alert behavior and validation](docs/PORTAL_VERIFICATION.md#alerts-map-and-gpsplate-evidence).

## Run the AI models

See [portal checks and sample videos](docs/PORTAL_VERIFICATION.md) for the multi-video setup, controls, verified coverage, and model/browser limitations.

Weights and analysis media are downloaded from versioned release assets rather than stored in source commits. Databases and credentials remain local. Follow [asset setup](docs/ASSETS.md) first.

```powershell
.venv/Scripts/python.exe scripts/check_assets.py
.venv/Scripts/python.exe run_models.py
# Or supply your own forward-facing car dashcam:
.venv/Scripts/python.exe run_models.py --source 'C:/path/to/dashcam.mp4'
```

On macOS/Linux use `.venv/bin/python`. Runs create timestamped folders under `edge_ai/outputs`; MP4s contain annotations and have no audio. The original input is preserved. The reference clip was processed in full: 240 frames, 24 FPS, 1280x720.

See [pothole settings](edge_ai/README.md). Raw extracted frames are not a labeled training dataset. Generic COCO weights are not a pothole-trained checkpoint.

To run all visual models on the same input video:

```powershell
.venv/Scripts/python.exe scripts/fetch_extended_models.py
.venv/Scripts/python.exe -m edge_ai.suite --source 'C:/path/to/dashcam.mp4'
```

The result is a timestamped folder under `edge_ai/outputs` containing `annotated.mp4`, per-frame detections and a summary. The Video Analysis page also offers selectable model profiles. [Extended model instructions](docs/EXTENDED_MODELS.md) explain experimental outputs and fixed-camera requirements.

## Checks

```powershell
.venv/Scripts/python.exe -m unittest discover -s edge_ai/tests -p "test_*.py"
Push-Location backend
../.venv/Scripts/python.exe -m pytest tests -q
Pop-Location
npm --prefix user_portal run build
npm --prefix government_portal run build
```

The AI unit tests use fixtures and require no model downloads. Backend tests use isolated state and exercise upload profile validation. GitHub Actions is configured for tests, lint, and frontend builds; it has not run on GitHub for these changes yet. Existing lint warnings are non-blocking.

## Layout

```text
backend/            FastAPI API, database models, services and tests
edge_ai/            Detectors, training utilities and video processing
user_portal/        Citizen React application
government_portal/  Government React application
scripts/            Setup and asset verification
docs/               Asset provenance and sharing instructions
.github/workflows/  Automated checks
start.ps1           Windows application launcher
run_models.py       Both-model video runner
```

See [GitHub preparation notes](docs/GITHUB.md). Third-party model/data licenses are separate from source-code ownership. No project-wide license has been selected.
