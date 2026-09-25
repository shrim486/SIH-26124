# AI-Powered Urban Intelligence

FastAPI backend, React citizen and government portals, and pothole/damaged-road detection from car dashcam videos.

## Current capabilities

- Pothole ONNX inference: overlapping road crops, confidence-labeled boxes, H.264 MP4 and per-frame JSONL.
- Damaged-road inference: separate RDD checkpoint filtering longitudinal, transverse and alligator cracks.
- Backend: event ingestion, duplicate handling, government authentication, road issues, alerts and dashboards.
- Portals: citizen reporting/maps and government dashboards.

AI inference runs offline; sending geolocated AI events to the backend is not implemented. Some auth/traffic/route modules remain test stubs. Predictions can miss damage or produce false positives; no measured accuracy is claimed. Training/evaluation require labeled datasets, which are not included.

## Setup after cloning

Use Python 3.10 (tested), Node.js 22.12+ and npm. Run commands from this repository root:

```powershell
python scripts/setup.py
```

This creates `.venv`, installs Python dependencies and both portals with `npm ci`, and creates missing `.env` files without replacing existing configuration. Government credentials and a generated signing secret are in `backend/.env`; keep that file private. For configuration only: `python scripts/setup.py --config-only`.

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

## Run the AI models

Weights, videos, databases, and datasets are excluded from Git. Follow [asset setup](docs/ASSETS.md) first.

```powershell
.venv/Scripts/python.exe scripts/check_assets.py
.venv/Scripts/python.exe run_models.py
# Or supply your own forward-facing car dashcam:
.venv/Scripts/python.exe run_models.py --source 'C:/path/to/dashcam.mp4'
```

On macOS/Linux use `.venv/bin/python`. Runs create timestamped folders under `edge_ai/outputs`; MP4s contain annotations and have no audio. The original input is preserved. The reference clip was processed in full: 240 frames, 24 FPS, 1280x720.

See [pothole settings](edge_ai/README.md). Raw extracted frames are not a labeled training dataset. Generic COCO weights are not a pothole-trained checkpoint.

## Checks

```powershell
.venv/Scripts/python.exe -m unittest discover -s edge_ai/tests -p "test_*.py"
Push-Location backend
../.venv/Scripts/python.exe -m pytest tests -q
Pop-Location
npm --prefix user_portal run build
npm --prefix government_portal run build
```

The 17 AI tests use fixtures and require no model downloads. The backend test uses an isolated in-memory database and authenticates before accessing government endpoints. GitHub Actions is configured for tests, lint, and frontend builds; it has not run on GitHub yet. Existing lint warnings are non-blocking.

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
