"""Compare drivable alternatives with nearby active reports; no safety guarantees."""
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import cos, radians, hypot, isfinite
from threading import BoundedSemaphore
import json
from fastapi import HTTPException
from app.schemas.journey import JourneyPoint
from app.services.alert_service import list_alerts
from app.services.map_provider import road_routes
from app.core.config import settings

METRES = 111195.0
# Preference costs are ranking units, NOT minutes of measured delay.
WEIGHTS = {'accident':14, 'waterlogging':10, 'road_damage':5, 'pothole':3,
           'congestion':4, 'bottleneck':5, 'missing_divider':3,
           'missing_zebra_crossing':2, 'traffic_sign_issue':2, 'rash_driving':2}
# Assigned map references for saved analysis clips; only include with the existing
# explicit include_assigned route-comparison option.
ATTACHED_CLIP_POINTS = [
    ('bellary-yelahanka-pothole', 'pothole', 'NH 44 · Bellary Road, Yelahanka', 13.1000, 77.5962),
    ('bellary-hebbal-accident', 'accident', 'NH 44 · Hebbal Flyover', 13.0361, 77.5971),
    ('mekhri-circle-road-damage', 'road_damage', 'Bellary Road, Mekhri Circle Flyover', 13.0162, 77.5918),
    ('koramangala-ejipura-pothole', 'pothole', '100 Feet Road, Ejipura Flyover', 12.9422, 77.6228),
    ('orr-bellandur-congestion', 'congestion', 'Outer Ring Road, Bellandur Flyover', 12.9270, 77.6766),
    ('orr-marathahalli-congestion', 'congestion', 'Outer Ring Road, Marathahalli Bridge', 12.9591, 77.6972),
    ('old-madras-krpuram-waterlogging', 'waterlogging', 'Old Madras Road, KR Puram Flyover', 13.0060, 77.6951),
    ('whitefield-hopefarm-road-damage', 'road_damage', 'Whitefield Main Road, Hope Farm Flyover', 12.9697, 77.7490),
]
RADII = {'accident':120, 'waterlogging':120, 'congestion':180, 'bottleneck':180}
LIFETIMES = {'accident':6*3600, 'waterlogging':24*3600, 'congestion':1800,
             'bottleneck':1800, 'rash_driving':1800, 'helmet_violation':3600,
             'triple_riding':3600, 'traffic_violation':3600}
_planning = BoundedSemaphore(2)


def distance(a, b):
    """Local distance in metres for the bounded city-route extent."""
    scale = cos(radians((a[1] + b[1]) / 2))
    return hypot((a[0]-b[0])*METRES*scale, (a[1]-b[1])*METRES)


def nearest_on_path(point, coordinates):
    scale = cos(radians(point[1]))
    best = (float('inf'), 0.0, 0)
    progress = 0.0
    for index, (a,b) in enumerate(zip(coordinates, coordinates[1:])):
        ax, ay = (a[0]-point[0])*METRES*scale, (a[1]-point[1])*METRES
        bx, by = (b[0]-point[0])*METRES*scale, (b[1]-point[1])*METRES
        dx, dy = bx-ax, by-ay
        length = hypot(dx,dy)
        t = min(1, max(0, -(ax*dx+ay*dy)/(length*length))) if length else 0
        separation = hypot(ax+t*dx, ay+t*dy)
        if separation < best[0]:
            best = (separation, progress+t*length, index)
        progress += length
    return best


def active_reports(db, include_assigned=False):
    now = datetime.now(timezone.utc)
    result, excluded_assigned, excluded_stale, excluded_unlocated = [], 0, 0, 0
    for row in list_alerts(db, active_only=True, include_demo=True):
        if row.get('issue_status') in {'resolved','closed'}:
            continue
        if row['is_demo'] and not include_assigned:
            excluded_assigned += 1
            continue
        timestamp = datetime.fromisoformat(row['created_at']) if row['created_at'] else now
        age = max(0, (now-timestamp).total_seconds())
        if not row['is_demo'] and age > LIFETIMES.get(row['alert_type'], float('inf')):
            excluded_stale += 1
            continue
        latitude, longitude = row.get('latitude'), row.get('longitude')
        if not (isinstance(latitude, (int, float)) and isinstance(longitude, (int, float))
                and isfinite(latitude) and isfinite(longitude)
                and abs(latitude) <= 90 and abs(longitude) <= 180):
            excluded_unlocated += 1
            continue
        result.append({key: row.get(key) for key in (
            'id','event_id','alert_type','latitude','longitude','severity','created_at',
            'location_name','location_source','is_demo','evidence_available')})
    if include_assigned:
        result.extend({
            'id': f'sample-road-{video_id}', 'event_id': None, 'video_id': video_id,
            'alert_type': alert_type, 'latitude': latitude, 'longitude': longitude,
            'severity': 'medium', 'created_at': None, 'location_name': location_name,
            'location_source': 'simulated_map_reference', 'is_demo': True,
            'evidence_available': True, 'evidence_only': True, 'is_map_attachment': True,
        } for video_id, alert_type, location_name, latitude, longitude in ATTACHED_CLIP_POINTS)
    else:
        excluded_assigned += len(ATTACHED_CLIP_POINTS)
    return result, excluded_assigned, excluded_stale, excluded_unlocated


def score_leg(route, reports):
    coordinates = route['geometry']['coordinates']
    xs, ys = [c[0] for c in coordinates], [c[1] for c in coordinates]
    min_x,max_x,min_y,max_y = min(xs),max(xs),min(ys),max(ys)
    matches = []
    for report in reports:
        point = [report['longitude'], report['latitude']]
        if not (min_x-.01 <= point[0] <= max_x+.01 and min_y-.003 <= point[1] <= max_y+.003):
            continue
        separation, progress, segment = nearest_on_path(point, coordinates)
        radius = RADII.get(report['alert_type'],80)
        if separation > radius:
            continue
        severity = {'low':.6,'medium':1,'high':1.8,'critical':3}.get(report['severity'],1)
        risk = WEIGHTS.get(report['alert_type'],0)*severity*max(.25,1-separation/radius)
        urgent = report['alert_type'] == 'accident' or (risk > 0 and report['severity'] in {'high','critical'})
        matches.append(dict(report, distance_from_route_m=round(separation), along_route_m=round(progress),
                            risk_points=round(risk,2), high_priority=urgent, affects_ranking=risk>0,
                            _segment=segment))
    return dict(route, matches=matches, risk_points=sum(item['risk_points'] for item in matches))


def combine(choices, points, stop_minutes):
    candidates = {}
    for legs in product(*choices):
        coords, alerts, summary, details, traffic_sections = [], {}, [], [], []
        metres, seconds = 0.0, 0.0
        traffic_delay_seconds, traffic_delay_known = 0.0, True
        traffic_aware = True
        for index, leg in enumerate(legs):
            coords.extend(leg['geometry']['coordinates'] if not coords else leg['geometry']['coordinates'][1:])
            for item in leg['matches']:
                if item['id'] not in alerts:
                    alerts[item['id']] = dict(item, along_route_m=round(item['along_route_m']+metres))
            names = [row.get('summary','') for row in leg.get('legs',[]) if row.get('summary')]
            summary.extend(names)
            traffic_aware = traffic_aware and leg.get('traffic_aware', False)
            traffic_sections.extend(leg.get('traffic_sections', []))
            delay = leg.get('traffic_delay_seconds')
            if delay is None:
                traffic_delay_known = False
            else:
                traffic_delay_seconds += delay
            details.append(dict(from_label=points[index].label or f'Point {index+1}',
                to_label=points[index+1].label or f'Point {index+2}', distance_km=round(leg['distance']/1000,2),
                duration_minutes=round(leg['duration']/60,1), roads='; '.join(names),
                traffic_aware=leg.get('traffic_aware', False),
                traffic_delay_seconds=leg.get('traffic_delay_seconds'),
                stop_minutes=points[index+1].dwell_minutes if index+1<len(points)-1 else 0))
            metres += leg['distance']; seconds += leg['duration']
        identity = sha256(json.dumps(coords,separators=(',',':')).encode()).hexdigest()[:12]
        matches = sorted(alerts.values(), key=lambda row:row['along_route_m'])
        candidates[identity] = dict(id=identity, geometry={'type':'LineString','coordinates':coords},
            distance_km=round(metres/1000,2), driving_minutes=round(seconds/60,1),
            stop_minutes=stop_minutes, duration_minutes=round(seconds/60+stop_minutes,1),
            risk_points=round(sum(item['risk_points'] for item in matches),2),
            high_priority_count=sum(item['high_priority'] for item in matches),
            hazard_count=sum(item['affects_ranking'] for item in matches), report_count=len(matches),
            traffic_aware=traffic_aware,
            traffic_delay_seconds=round(traffic_delay_seconds) if traffic_aware and traffic_delay_known else None,
            traffic_sections=traffic_sections,
            issues=[{k:v for k,v in item.items() if not k.startswith('_')} for item in matches],
            roads='; '.join(dict.fromkeys(summary)), legs=details)
    return list(candidates.values())


def plan_journey(db, payload):
    if not _planning.acquire(blocking=False):
        raise HTTPException(429, 'Route planner is busy. Please try again shortly.', headers={'Retry-After':'3'})
    try:
        return _plan(db, payload)
    finally:
        _planning.release()


def _plan(db, payload):
    points = [payload.origin, *payload.stops, payload.destination]
    lengths = [distance([a.longitude,a.latitude],[b.longitude,b.latitude]) for a,b in zip(points,points[1:])]
    if min(lengths) < 30:
        raise HTTPException(422, 'Consecutive start, stop and destination points must be at least 30 metres apart.')
    if sum(lengths) > 150000:
        raise HTTPException(422, 'Choose a city journey within 150 km between the selected points.')
    reports, excluded_assigned, excluded_stale, excluded_unlocated = active_reports(db,payload.include_assigned)
    choices, warnings = [], []
    for a,b in zip(points,points[1:]):
        choices.append([score_leg(route,reports) for route in road_routes([a,b])])
    # Ask the road router for real alternatives that pass around several of the
    # highest-risk reports. More extra time expands both the target set and clearance.
    detour_routes_generated = 0
    if payload.max_extra_minutes > 0:
        target_limit = 1 if payload.max_extra_minutes <= 5 else 2 if payload.max_extra_minutes <= 15 else 4 if payload.max_extra_minutes <= 30 else 6
        detour_failed = False
        for leg_index, options in enumerate(choices):
            source_route = min(options, key=lambda row: (row['duration'], row['risk_points']))
            targets = [hazard for hazard in source_route['matches']
                       if hazard['risk_points'] > 0
                       and min(distance([hazard['longitude'], hazard['latitude']], [point.longitude, point.latitude])
                               for point in points) > 120]
            targets = sorted(targets, key=lambda hazard: (-hazard['risk_points'], hazard['along_route_m']))[:target_limit]
            targets.sort(key=lambda hazard: hazard['along_route_m'])
            if not targets:
                continue

            side_points = {-1: [], 1: []}
            for hazard in targets:
                coordinates = source_route['geometry']['coordinates']
                segment = max(0, min(hazard['_segment'], len(coordinates) - 2))
                a,b = coordinates[segment:segment+2]
                scale = cos(radians(hazard['latitude']))
                dx,dy = (b[0]-a[0])*METRES*scale,(b[1]-a[1])*METRES
                length = hypot(dx,dy)
                if not length or scale <= 0:
                    continue
                radius = RADII.get(hazard['alert_type'], 80)
                clearance = max(350, min(1200, radius + 250 + payload.max_extra_minutes*10))
                for sign in (-1,1):
                    latitude = hazard['latitude'] + sign*dx/length*clearance/METRES
                    longitude = hazard['longitude'] - sign*dy/length*clearance/(METRES*scale)
                    if not (-85 <= latitude <= 85 and -180 <= longitude <= 180):
                        continue
                    via = JourneyPoint(latitude=latitude, longitude=longitude)
                    if min(distance([via.longitude, via.latitude], [point.longitude, point.latitude]) for point in points) < 100:
                        continue
                    if any(distance([via.longitude,via.latitude], [other.longitude,other.latitude]) < 150 for other in side_points[sign]):
                        continue
                    side_points[sign].append(via)

            for via_points in side_points.values():
                if not via_points:
                    continue
                try:
                    route = road_routes([points[leg_index], *via_points, points[leg_index+1]],alternatives=False)[0]
                    choices[leg_index].append(score_leg(route,reports))
                    detour_routes_generated += 1
                except HTTPException:
                    detour_failed = True
        if detour_failed:
            warnings.append('A targeted hazard-avoidance detour could not be calculated. Available road routes were still compared.')
    candidates = combine(choices,points,sum(stop.dwell_minutes for stop in payload.stops))
    fastest = min(candidates,key=lambda row:(row['duration_minutes'],row['risk_points']))
    eligible = [row for row in candidates if row['duration_minutes'] <= fastest['duration_minutes']+payload.max_extra_minutes+.001]
    lower_risk = min(eligible,key=lambda row:(row['high_priority_count'],row['risk_points'],row['duration_minutes']))
    min_high = min(row['high_priority_count'] for row in eligible)
    balanced = min((row for row in eligible if row['high_priority_count']==min_high),
                   key=lambda row:(row['duration_minutes']+row['risk_points'],row['risk_points']))
    recommended = {'fastest':fastest,'balanced':balanced,'lower_risk':lower_risk}[payload.preference]
    roles = {'Fastest':fastest['id'],'Balanced':balanced['id'],'Lower exposure':lower_risk['id']}
    selected_ids = list(dict.fromkeys([recommended['id'],fastest['id'],lower_risk['id'],balanced['id']]))
    # Also show a distinct time/risk trade-off if recommendation roles coincide.
    for row in sorted(eligible,key=lambda row:(row['risk_points'],row['duration_minutes'])):
        if len(selected_ids)>=3:
            break
        if row['id'] not in selected_ids:
            selected_ids.append(row['id'])
    selected = [next(row for row in candidates if row['id']==identity) for identity in selected_ids]
    for row in selected:
        row['roles'] = [role for role,identity in roles.items() if row['id']==identity]
        row['recommended'] = row['id']==recommended['id']
        row['extra_minutes'] = round(row['duration_minutes']-fastest['duration_minutes'],1)
        row['avoided_hazards'] = max(0,fastest['hazard_count']-row['hazard_count'])
        row['reported_hazard_free'] = row['hazard_count'] == 0
    if recommended['high_priority_count']:
        warnings.append('The recommended route still passes near high-priority reports or assigned clip points. Review their locations before travelling.')
    if len(candidates)==1:
        warnings.append('The road provider returned only one distinct route for these points.')
    if payload.include_assigned:
        warnings.append('Assigned positions and clip map references are included for route comparison; their recording locations are unverified and may not reflect current conditions.')
        warnings.append('Some clip sources are unknown or outside Bengaluru; the route comparison treats their map references as hypothetical points, not verified incidents.')
    if reports and not any(row['hazard_count'] == 0 for row in eligible):
        warnings.append(f'No compared route avoided all scored mapped hazards within {payload.max_extra_minutes} extra minutes. The recommendation has the lowest exposure found among the available routes.')
    if not reports:
        warnings.append('No eligible active reports are available. This does not confirm that the roads are clear.')
    all_matches = {item['id']: item for row in selected for item in row['issues']}
    return dict(routes=selected,recommended_route_id=recommended['id'],points=[p.model_dump() for p in points],
        issues=list(all_matches.values()), generated_at=datetime.now(timezone.utc).isoformat(),
        preference=payload.preference, max_extra_minutes=payload.max_extra_minutes,
        eligible_reports=len(reports),
        eligible_alert_count=sum(not item.get('is_map_attachment') for item in reports),
        eligible_clip_count=sum(bool(item.get('is_map_attachment')) for item in reports),
        excluded_assigned_count=excluded_assigned, excluded_stale_count=excluded_stale,
        excluded_unlocated_count=excluded_unlocated, includes_assigned=payload.include_assigned,
        compared_routes=len(candidates), detour_routes_generated=detour_routes_generated,
        warnings=list(dict.fromkeys(warnings)),
        traffic_aware=settings.ROUTING_PROVIDER == 'tomtom',
        traffic_provider='TomTom' if settings.ROUTING_PROVIDER == 'tomtom' else None,
        eta_basis=(
            'TomTom traffic-aware driving estimate plus planned stop time. Traffic reflects data available when this comparison was calculated and can change.'
            if settings.ROUTING_PROVIDER == 'tomtom' else
            'Road-network driving estimate plus planned stop time. Live traffic is not connected with the current OSRM provider.'
        ),
        hazard_basis='Nearby active reports within 80–180 m of the route; adjacent roads may be included.',
        attribution=('TomTom Routing / TomTom Traffic · OpenStreetMap contributors' if settings.ROUTING_PROVIDER == 'tomtom'
                     else 'OpenStreetMap contributors · OSRM / FOSSGIS'),
        # Compatibility for callers of the previous route endpoint.
        route=[{'latitude':p[1],'longitude':p[0]} for p in recommended['geometry']['coordinates']],
        distance_km=recommended['distance_km'], duration_minutes=recommended['duration_minutes'])
