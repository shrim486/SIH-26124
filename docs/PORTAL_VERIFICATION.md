# Portal demonstrations and checks

The local citizen map is http://127.0.0.1:5173/map. Government records are at
http://127.0.0.1:5174/detections; use the configured government account.
Every published record links to an annotated MP4 and frames containing that
record's model prediction. All sample coordinates and timestamps are simulated.
They create explicitly labeled in-app demo alerts; they do not trigger
emergency dispatch or create enforcement records.

## Model coverage

Twelve types can be analyzed and published: potholes, damaged roads, waterlogging,
road dividers, zebra crossings, traffic signs, accidents, plates/OCR, helmets,
triple riding, congestion and bottlenecks. Congestion and bottlenecks use tracked
vehicle motion rules with a fixed camera; they are not trained event classifiers.

The September 27 video checks produced candidates for eight types: pothole,
damaged road, waterlogging, zebra crossing, traffic sign, accident, number plate,
and helmet. These are demonstrations, not an accuracy benchmark.

Road dividers and triple riding did not produce usable positive detections on
the tested videos. Congestion and bottleneck analyses completed but did not meet
their queue thresholds. Their videos remain available, with zero candidates;
no positive map detections were fabricated. Additional checkpoint probes are
recorded in [model-probes.json](model-probes.json). Those checkpoints were not
adopted after failing the sample checks.

## Reproduce the video demonstrations

From the repository root, using the configured Python environment:

```powershell
python scripts/fetch_demo_videos.py
python scripts/run_demo_videos.py
# Start the backend first; publication reads only the local government credentials.
python scripts/publish_demo_detections.py
# For installations with the previous rider/waterlogging map examples:
python scripts/retire_superseded_demos.py
python scripts/retire_superseded_demos.py --apply
# Link previously published major detections to the new Alerts map:
python scripts/sync_detection_alerts.py
python scripts/sync_detection_alerts.py --apply
```

Downloads are versioned where supported and hashed in [multi-demo-sources.json](multi-demo-sources.json).
The runner creates short excerpts at 12 FPS, preserving playback duration and
recording each excerpt's offset and camera type. The original sources remain
unchanged. Some samples are roadside/handheld footage; traffic motion rules run
only on fixed cameras. The `triple_riders` source is a staged film excerpt used
by its publisher, and is labeled as such. Public examples are not claimed to
have been recorded at their Bengaluru map coordinates.

Publishing is repeatable: existing run/segment links are reused. The accident
demo from the earlier run is preserved. Videos, weights, databases, downloaded
frames and credentials are ignored by Git.

## Replacement rider video and map selection

`demo_slow_riders` uses the opening 16 seconds of a different on-bike video,
published in the sample folder linked by
[Pratham Jaiswal's project](https://github.com/pratham-jaiswal/two-wheeler-traffic-rule-violation).
The source file is `vid1.mp4`; its public download URL and SHA-256 are in the
manifest. The excerpt keeps 1920×1080 resolution and normal playback duration,
resampled at 12 FPS (192 analyzed frames). No detection boxes were present in
the input; the local helmet and FastALPR models produced the output boxes.

Actual positive frames: **62 with helmet, 53 without helmet, and 61 with a
number plate**. The bare-headed examples include pillion passengers. These
are repeated frame observations, not counts of unique people. OCR produced
text on 42 plate-box observations, with some missing/incorrect characters;
no OCR accuracy or correct registration number is claimed.

The helmet map record (#13) and plate record (#14) link to the same new MP4.
Helmet evidence sampling includes both detected classes. Green boxes label
helmets, red boxes label bare heads, blue boxes label plates, and grey boxes
show vehicle tracks. The player also offers 0.5×/0.75× review speeds.
Temporal confirmation cannot apply a previous helmet class to a different
current head box. The detector still selects one head per tracked motorcycle;
it does not reliably detect every rider or every plate in every frame.

The map now keeps only the dedicated waterlogging video (#10). Old rider
records (#3, #11, #12) and repeated waterlogging records (#6, #7, #8) were
backed up under `.runtime/retired-demos-*.json` and retired. Their source videos
and saved analyses remain available. The publisher's curated selection does
not re-add those examples. Retirement requires the replacement evidence to be
published first and only touches matching demo records. Bengaluru placement
and recording times remain explicitly simulated.

## Controls checked

| Area | Check |
| --- | --- |
| Government sign-in | Authenticated endpoints, invalid/absent credentials, sign-out handlers |
| Citizen reports | Submit, coordinate validation, saved report listing, refresh/error state |
| User map | Type filter, demo toggle, focused incident URL, evidence link; map position preserved across unchanged polls |
| Notifications | Notification button opens the active-alert feed |
| Road issues | Type/status filters, supported status updates, invalid updates rejected |
| Violations | Shared map issues, no-helmet/plate evidence, open/review/resolve/reopen actions; no automatic enforcement |
| Alerts | Map, filters, coordinates, private plate evidence, dismiss/reactivate and resolve/reopen; persistent status |
| Analytics | Actual analytics endpoint and detection/severity/violation counts |
| Detected Issues Map | Curated actionable issues, status/type/demo filters, map/video links, action notes and status history |
| Issue evidence | Videos & Images library for actionable issues; embedded players/images on issue and government alert pages; exact event links, full images, frame seeking, media authorization and byte ranges |
| Fleet | Bus registration/edit, camera registration/configured status, last GPS position, freshness and linked bus issues |
| Video uploads | Individual models, camera validation, bottleneck zones, empty-file errors, saved job recovery after restart |

Automated backend tests exercise the APIs behind these controls, including all
12 publication types and duplicate prevention. Both portal production builds
are checked. Browser automation was unavailable in this session: actual clicks,
responsive layouts, geolocation permission prompts, and visual playback across
browsers still require a connected browser/manual check. API and build results
are not claimed as a visual end-to-end test of every button.

Latest local results: 44 backend tests passed; the prior AI check passed 28 tests. Both frontend
production builds passed, and 14 live API read routes responded successfully.
The map contains 8 linked demo records across eight types, with 42 evidence
images decoded successfully. All frames in the eleven additional annotated MP4s
were decoded and their H.264 encoding checked. A real six-frame upload completed
inference, polling and video streaming. Completed upload status and media were
also checked after a backend restart. Resolving a newly reported road issue now
updates its linked citizen report and expires its associated safety alert.
The five actionable demo issues now populate the government pages (three road,
one accident, one no-helmet). Live API checks resolved and reopened all five,
verified that the same public alert IDs were restored, and checked their private
video streams and 27 linked frame references. All five were left open. Eight
source map records and their media were preserved; ordinary plate/sign/crossing
records are excluded from the government action list. Fleet is correctly empty
until buses and cameras are registered. See [operations guide](GOVERNMENT_OPERATIONS.md).

## Alerts map and GPS/plate evidence

Citizen Alerts: http://127.0.0.1:5173/alerts

Government Alerts: http://127.0.0.1:5174/alerts

Both pages show active issues on a map, with type filters, a demo toggle,
coordinates, time, and incident evidence links. Government users can
dismiss/reactivate alerts and review associated plate readings. Dismissal
removes the alert from the citizen feed; synchronization preserves it.
Pages poll every 15 seconds and preserve the map view when data is unchanged.

Five current demo alerts link to the accident, damaged road, pothole,
waterlogging, and no-helmet incidents. No-helmet is included in the traffic
violations filter. There is still only one waterlogging example. Ordinary
helmeted riders, standalone plate observations, signs and zebra crossings do
not create safety alerts. Positive congestion, bottleneck and other supported
traffic-violation events can create alerts when they are supplied.

`AlertEvent` links each alert to its source event. New video publications
create eligible alerts automatically. `sync_detection_alerts.py --apply`
backfills existing published detections, saving a row backup under `.runtime`.
The event coordinates and timestamp are retained exactly. Demo data
is labeled in both feeds and can be excluded with `/user/alerts?include_demo=false`.
Nearby navigation alerts exclude demos unless `include_demo=true` is explicit.

Helmet analysis now includes `number_plate` automatically, for both uploaded
videos and the unified CLI. Associations require a no-helmet prediction and
a plate inside exactly one matching tracked motorcycle in the **same frame**.
Ambiguous overlapping vehicles and unrelated frames are rejected. Selected
frames are added to the incident evidence gallery and timestamp links seek to
the matching frame in the same annotated video. OCR candidates are shown in
government responses/UI, with uncertain/unreadable states and no claim of
verified registration. Public alert, map and event-list responses omit plate
readings. Even repeated OCR remains a review candidate.

Current rider evidence links one uncertain OCR candidate and one unreadable
plate; the text is not accurate enough for automatic enforcement. No plate is
assigned merely because it appears elsewhere in the video. The existing
one-head-per-motorcycle model limitation still applies.

GPS is **not inferred from road pixels**. Live ingestion at `POST /api/v1/events`
requires finite latitude/longitude in valid ranges; camera telemetry can mark
`metadata.location_source` as `camera_gps`. Those coordinates are copied to
the alert. Uploaded videos without location telemetry need the publication
form's incident coordinates/time. Existing Bengaluru points remain simulated,
as requested, because these sample recordings have no verified GPS.

Validation includes a real six-frame `helmet` upload that automatically
ran helmet and plate/OCR together, survived backend restart, and produced an
annotated video. Live alert checks cover all five types, location/evidence
matching, 27 linked images, byte-range video delivery, demo filtering, and
dismiss/sync/reactivate behavior. Browser connection was unavailable; visual
click-through testing has not been claimed.
