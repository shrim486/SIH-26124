# Fleet monitoring and portal records

The government portal is served at http://127.0.0.1:5174; the citizen portal at http://127.0.0.1:5173.

## Shared incidents and evidence

Both dashboards, the citizen incident map, government detected-issues map, alerts pages and the government recordings library use the same canonical alert records. Supported categories include no helmet, traffic violations, waterlogging, accidents, potholes, road damage, congestion and bottlenecks. Ordinary model observations such as a detected number plate, normal sign or crosswalk are not safety alerts.

- `GET /api/v1/user/records` provides the public records and count fields.
- `GET /api/v1/government/records` requires government authentication and includes private review fields.
- `?archive=true` selects resolved, dismissed or expired alerts. The default is active alerts.
- The response includes `records`, `total`, `mapped`, `missing_location`, `with_evidence` and `updated_at`. It uses the shared alert service's latest-500-record window, deduplicated by alert ID.
- Each card uses an incident title and location, with a smaller stable `INC-00001` reference. Legacy alerts without an event use an `ALT-00001` reference. IDs in URLs are unchanged.
- Dashboard cards and map popup **Open video & images** links lead to the exact event's authenticated evidence page. The dashboard does not preload all videos. Alert cards offer an explicit evidence preview; the dedicated page shows the video and detected frames together.
- The recordings library lists every record in the selected active/archive set, including records without footage. Missing coordinates remain visible in the list and count, but do not produce an invented map pin.
- Category case pages retain review notes, resolution/reopening and status history. Their default active-alert filter matches the map. Historical cases can be selected explicitly.

Different locations are not assigned the same footage as separate incidents of one type. When publishing assigned locations, the backend rejects reuse of a recording already attached to that type, including a byte-identical copied output or the same known original source URL. A different source recording is required. Multiple kinds actually detected in one recording can still reference their corresponding segments. Genuine, located recordings may contain multiple distinct incidents. Republishing the same segment remains idempotent; existing incident data is retained.

Evidence lookup uses its stored run and segment identity. If reprocessing removes that segment, the API returns a conflict instead of substituting another segment or the entire recording. Video-source provenance and assigned-location fields remain intact. Neither portal's public feed exposes plate OCR or vehicle registrations.

## Fleet controls

At `/fleet`, operators can:

- Register and edit buses, route numbers and in-service status.
- Search by bus/route; filter recent GPS, overdue GPS, no telemetry, manual positions, out-of-service vehicles or vehicles needing attention.
- Refresh manually or pause/resume 15-second updates; export the filtered register as CSV.
- Inspect last recorded and received times, coordinates, telemetry source, cameras and linked cases.
- Follow a selected vehicle, fit the fleet, or inspect a recorded position trail for 1, 6, 24 or 168 hours.
- Register/edit camera codes and mounting positions; change configured status independently of reported camera health.
- Supply an explicitly manual position without marking a vehicle online.

No vehicles, movement, camera feeds or GPS reports are generated automatically. Recent device GPS means a recording within two minutes (with up to 60 seconds of tolerated clock skew). Manual and inactive vehicles never count as online. Camera registration or configured `active` status does not establish camera health.

## Telemetry integration

Fleet monitoring now also supports actual preview images from registered cameras. See [live-camera setup](LIVE_CAMERAS.md) for the edge connector, protected frame APIs, live/stale status and retention. This is separate from heartbeat-only telemetry below.

Existing government bearer authentication is required for these endpoints; keep credentials outside source control.

`POST /api/v1/government/fleet/buses/{id}/position` accepts actual latitude, longitude, timezone-aware `recorded_at`, and `source: device|manual`. The portal always uses `manual`. Accepted updates append to `fleet_position_history` and update the latest position in one transaction. Duplicate or older timestamps are rejected. `GET /api/v1/government/fleet/buses/{id}/history?hours=24&limit=1000` returns chronological points; limits are 1–168 hours and 1–3000 points. A `truncated` flag indicates older points omitted from the response. Existing positions predating history collection remain available as a fallback.

Trails join recorded device points only, with breaks for manual entries and gaps over five minutes. These lines are not road-snapped routes or an assertion of continuous tracking. History collection starts with new reports; this change does not invent past positions. Stored history has no automatic retention purge; operators should establish a retention policy for a deployed service.

`POST /api/v1/government/fleet/cameras/{id}/heartbeat` accepts:

```json
{
  "recorded_at": "2026-09-27T12:00:00+05:30",
  "last_frame_at": "2026-09-27T11:59:59+05:30",
  "state": "ok",
  "message": ""
}
```

Use the device's actual heartbeat and captured-frame timestamps. `state` is `ok` or `error`; `last_frame_at` is optional. The system distinguishes no report, stale report, device error, no recent frames and recent frames. Frame time cannot exceed the heartbeat time. Naive/future timestamps and out-of-order updates are rejected. A recent frame report is device telemetry, not a server-side stream probe or live video player.

`PUT /api/v1/government/fleet/cameras/{id}` updates `camera_code` and `camera_type` with the existing `bus_id`. Reassignment to another bus is rejected to preserve historical associations; register a new camera for that bus. Configured status remains a separate PATCH action.

Known camera IDs on ingested detections supply their registered bus ID. Contradicting that bus ID is rejected. When multiple vehicles report one deduplicated incident, each vehicle's issue list includes the shared case. The existing acceptance of externally supplied legacy bus/camera IDs is retained; such IDs do not auto-register a vehicle.

New `fleet_position_history` and `camera_heartbeats` tables are created at API startup. Existing data is retained; a SQLite backup was created locally before restart.

## UI and validation

The portals share typography, spacing, navigation and record styles through `shared/portal-polish.css`. Headlines use plain issue names. Videos retain their aspect ratio and detection frames fit within consistent image cards, with accessible focus indicators and responsive layouts. Media stays behind government authentication.

Backend tests cover shared counts and references, archive transitions, missing-location handling, public privacy, distinct footage, deleted segments, camera attribution, GPS history, camera health and existing route/evidence workflows. The full suite passes **76 tests**. Both production builds pass. Lint has warnings (primarily existing effect and component-export rules), but no errors. Browser tooling had no connected browser, so interactive click-through and visual verification could not be performed; builds and running API/media checks are not a substitute for those checks.

Local live verification is saved under `.runtime/fleet-records-verification.json` (ignored by Git).

The live check found **5 active records, 5 mapped incidents, 5 linked evidence records and no missing coordinates**. Every linked video returned a valid partial-content response and all **27 detected images** decoded successfully. No same-type incidents reused a video. The single current waterlogging record has its own linked recording; the distinct-footage rule was additionally tested with two isolated waterlogging cases. There are currently **no registered buses or cameras** in the local operational database. Register devices and send actual telemetry to populate fleet monitoring; automated tests used a separate database and did not add vehicles or incidents to the running app.
