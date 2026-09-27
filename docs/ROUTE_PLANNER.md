# Citizen route planner

Open **Plan Route** in the citizen sidebar or dashboard, or visit http://127.0.0.1:5173/plan-route.

1. Search for a pickup and drop-off, select a result, or use map pins / `latitude, longitude`. Location permission is requested only after **Use my location**.
2. Add up to three stops in travel order. Each stop can include 0–120 minutes of dwell time. Reorder, remove or reverse the trip as needed.
3. Choose Balanced, Fastest or Lower exposure and a maximum extra driving time (0–60 minutes).
4. Compare the route cards. Selecting a card draws that route and lists nearby reports in journey order. **Show on route** focuses an issue; **Show whole journey** restores the overview. **Find balanced routes** refreshes the reports and recommendation.

## Route selection

The backend requests actual driving geometries from OSRM for each consecutive pair of mandatory points. It combines available alternatives while preserving stop order. If a major hazard lies away from the mandatory points, it also tries two road-provider routes through offset points around the highest-weight avoidable report. Provider failures never fall back to a straight line or invented ETA.

The fastest candidate establishes the time budget. Within that budget, Balanced first minimizes the number of nearby high-priority reports, then minimizes driving minutes plus weighted hazard exposure. Lower exposure minimizes high-priority count, then exposure, then time. Fastest minimizes time. Up to three distinct alternatives are displayed; the provider may only return one. This is a comparison of retrieved candidates, not a globally optimal or guaranteed-safe route.

Weights are preference units, **not measured delay minutes**: accident 14, waterlogging 10, road damage 5, pothole 3, congestion 4, bottleneck 5, missing divider 3, missing crossing 2, sign issue 2, rash driving 2. Severity and proximity adjust these weights. Accidents and high/critical physical hazards receive high-priority treatment. Helmet, triple-riding and other violation reports remain informational; a missing helmet does not imply a blocked road. Private registrations and OCR candidates are not exposed.

Reports are matched to segments along the full route geometry, within 120 m for accidents/waterlogging, 180 m for congestion/bottlenecks, and 80 m otherwise. Adjacent or elevated roads may fall in the same radius; matching is geographic, not lane-aware. Reports repeated across route legs are counted once. Coordinates snap to drivable roads within 250 m. Consecutive requested points must be at least 30 m apart; the sum of straight-line leg distances must be at most 150 km.

## Data freshness and ETA

Only active reports for open/in-progress issues are scored. Resolved, closed and dismissed reports do not affect a new comparison. Latest 500 alerts are available through the shared alert service; old transient reports are excluded: accident 6 hours, waterlogging 24 hours, congestion/bottleneck/rash driving 30 minutes, and other violations 1 hour. Potholes and damaged roads remain eligible until resolved. These are local defaults, not confirmation of on-road conditions.

Existing footage has assigned Bengaluru positions, not verified camera GPS. Those records are excluded by default. **Include assigned map points in comparison** explicitly includes them with their provenance visible; this mode bypasses transient age limits for those assigned records. Use genuine GPS and recording times before relying on the reports for a real journey.

ETA is the provider's driving duration plus planned stop time. Live traffic, signal delays, weather and actual hazard delays are not connected. The interface says “approx.” and discloses this basis. No nearby reports does not confirm a clear road. Results are a snapshot; run the comparison again after issue updates.

## Configuration and providers

Backend defaults in `backend/.env.example`:

```dotenv
ROUTING_BASE_URL=https://routing.openstreetmap.de/routed-car
GEOCODING_BASE_URL=https://photon.komoot.io
MAP_USER_AGENT=UrbanIQ-RoutePlanner/1.0 (https://github.com/shrim486/SIH-26124)
```

The default public services require internet access. The app submits only explicit place searches, with a Bengaluru location bias, and routing coordinates. Searches are cached for 24 hours; road responses for 5 minutes. Hazards are rescored from the database on every comparison. A bounded in-memory cache and per-provider lock allow at most one outgoing request per 1.05 seconds per backend process, with a 15-second network timeout and two concurrent journey calculations. Busy/unavailable providers return actionable errors.

These public defaults suit light local use. For a public deployment, configure your own services or a provider that supports the expected volume; use shared rate limiting across backend workers. Attribution and a map-correction link are visible below the map. See the primary [OSRM API documentation](https://project-osrm.org/docs/v5.24.0/api/), [FOSSGIS server policy](https://routing.openstreetmap.de/about.html), and [Photon service documentation](https://github.com/komoot/photon).

## API and verification

`GET /api/v1/user/places?q=Koramangala%20Bengaluru` returns place labels and coordinates.

`POST /api/v1/user/route` accepts:

```json
{
  "origin": {"latitude": 13.1006982, "longitude": 77.5963454, "label": "Yelahanka"},
  "destination": {"latitude": 12.9357366, "longitude": 77.624081, "label": "Koramangala"},
  "stops": [],
  "preference": "balanced",
  "max_extra_minutes": 15,
  "include_assigned": false
}
```

The response includes candidate GeoJSON routes, recommended ID, driving/stop/total time, distance, nearby public issues, ordered legs, exclusion counts and warnings. Legacy `route`, `distance_km` and `duration_minutes` fields describe the recommendation. Former fixed traffic/hazard scores have been removed.

`backend/tests/test_journey_planner.py` uses isolated databases and controlled provider geometries to check hazard avoidance, time limits, stop order/dwell, segment proximity, privacy, report resolution/freshness, assigned-position opt-in, duplicate routes/reports, provider failures and invalid inputs. These tests verify application behavior, not real-world road safety or model accuracy.

Local verification on 27 September 2026 (India time): all **69 backend tests** passed and the citizen production build passed. Lint reported existing warnings in other components, with none in the route planner. Real provider checks returned two Yelahanka–Koramangala alternatives, with a recommendation of 23.28 km / 27.9 minutes; a five-minute midway stop produced 32.9 minutes total. A required stop at the existing assigned accident position returned its matching alert, 2 m from the road geometry, and a high-priority warning. No incident records were changed. Timing will vary with provider data and selected coordinates.

The normal Yelahanka–Koramangala comparison excluded all five assigned incidents by default; enabling them did not produce nearby matches on those two routes. That reflects their positions and the matching radius, not a claim that those roads are clear. Detailed local check results are saved in `.runtime/route-planner-verification.json` (ignored by Git). No browser was connected for interactive or visual verification.
