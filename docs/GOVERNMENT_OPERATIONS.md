# Government issue management and fleet monitoring

Open http://127.0.0.1:5174 and sign in using the configured government account.

See [fleet monitoring and shared portal records](FLEET_AND_PORTAL_RECORDS.md) for
the updated interface, matching map/recording counts, direct evidence links,
GPS history and camera-health endpoints.

Portal copy uses operational issue titles, with **assigned map location** and
**assigned time** fields for positions entered for visualization. Detailed
recording notes are under **Recording details**. Recording locations remain
explicitly unverified where no GPS was available.
Internal `demo`/`is_demo` fields retain their existing meaning and safeguards.

## Issue workflow

Road Issues, Accidents, Traffic Violations and Detected Issues Map use the same
event IDs as citizen map pins and government video evidence. The combined view
includes potholes, road damage, waterlogging, accidents, no-helmet candidates,
other supported traffic violations, congestion and bottlenecks. Ordinary plate,
sign, zebra-crossing and with-helmet observations are excluded. The old broad
All Detections and AI Detection Results navigation entries have been replaced.
The **Videos & Images** menu at `/ai-results` lists only actionable mapped
issues with linked evidence. Each selection displays its annotated video and
detected frame images. Direct `/ai-results?incident=ID` pages remain available.
Source analyses are retained on disk and in the analysis API.

Open a row or map pin, review its video/frames, optionally enter an action note,
then choose Start review, Resolve issue, Close issue or Reopen issue. The issue
page displays its video and images below the map/details. Each government alert
opens its own evidence page and offers an explicit inline preview. Selecting an image seeks to that moment
in the video; **Open full image** opens the image separately to inspect boxes.
Media failures offer retry controls. Reports without attached evidence show an
explicit empty state. Citizen alerts retain authenticated government evidence
links; protected footage is not published to the public feed. Status
changes are stored with the government username, timestamp and note. Repeating
the same status does not duplicate the history. The Alerts page also offers
Open issue, Resolve and Reopen actions.

Resolving/closing an issue expires its public alert. Reopening restores the
same alert ID. Dismissing an alert only hides the notification and does not
resolve the case. A resolved issue must be reopened before its alert can be
reactivated. Citizen maps retain the issue history as a grey resolved/closed pin.
Demo classification and coordinates are preserved through every status change.
No demo action creates a violation enforcement record or a fine. Plate OCR is
an unverified candidate requiring inspection of the linked rider/plate frame.

Government operations endpoints (bearer token required):

- `GET /api/v1/government/issues?category=road|accidents|violations|traffic&status=open|in_progress|resolved|closed&bus_id=ID`
- `PATCH /api/v1/government/issues/{event_id}/status` with `status` and optional `note`
- `GET /api/v1/government/issues/{event_id}/history`

## Fleet

The fleet page supports bus registration/editing (number, route, in-service
state), camera registration and configured status (active/maintenance/offline),
last reported locations on a map, and links to each bus's detected issues.
It polls every 15 seconds. Camera status is operator-maintained; it is not a
video-stream health probe. No bus positions or camera streams are fabricated.

Device GPS is considered recent for two minutes after its recording time.
Older positions are marked stale and retained as last known locations. Manual
locations and inactive buses are never labeled online. The local database has
no registered buses/cameras until an operator adds them.

Authenticated fleet endpoints:

- `GET /api/v1/government/fleet`
- `POST /api/v1/government/fleet/buses`: `bus_number`, `route_number`, `is_active`
- `PUT /api/v1/government/fleet/buses/{id}`: same complete bus fields
- `POST /api/v1/government/fleet/cameras`: `bus_id`, `camera_code`, `camera_type` (`front`, `rear`, `cabin`)
- `PATCH /api/v1/government/fleet/cameras/{id}`: `status`
- `POST /api/v1/government/fleet/buses/{id}/position`: payload below

```json
{
  "latitude": 13.02,
  "longitude": 77.6,
  "recorded_at": "2026-09-27T12:00:00+05:30",
  "source": "device"
}
```

Use actual device coordinates and recording time, including its timezone.
The example is illustrative. The portal's manual-location form uses
`source: manual`. Out-of-range coordinates, timezone-free/future times and
out-of-order position updates are rejected. These endpoints require government
authentication; keep credentials outside source control. A device integration
must send GPS updates to this endpoint before live tracking is available.
For detections, use the registered `bus_id`/`camera_id` with the existing event
ingestion endpoint and actual incident coordinates. A saved video has no bus
association unless one was supplied; demo footage is not a live fleet feed.

New `issue_actions` and `fleet_positions` tables are created at backend startup.
Existing Event, RoadIssue, Violation and Alert records are retained.

## Validation

Backend integration tests cover demo preservation, all main issue categories,
resolution/reopening, alert identity, private evidence access, legacy status
endpoints, repeated ingestion, fleet registration, camera status, GPS validation
and stale/manual/inactive states. Run `python -m pytest tests -q` in `backend`.
Both frontend builds are checked with `npm run build`. Browser automation was
unavailable, so visual click-through and responsive layout checks remain manual.
