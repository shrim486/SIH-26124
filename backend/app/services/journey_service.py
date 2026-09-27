"""Compare drivable alternatives with nearby active reports; no safety guarantees."""
from datetime import datetime, timezone
from hashlib import sha256
from itertools import product
from math import cos, radians, hypot
from threading import BoundedSemaphore
import json
from fastapi import HTTPException
from app.schemas.journey import JourneyPoint
from app.services.alert_service import list_alerts
from app.services.map_provider import road_routes

METRES = 111195.0
# Preference costs are ranking units, NOT minutes of measured delay.
WEIGHTS = {'accident':14, 'waterlogging':10, 'road_damage':5, 'pothole':3,
           'congestion':4, 'bottleneck':5, 'missing_divider':3,
           'missing_zebra_crossing':2, 'traffic_sign_issue':2, 'rash_driving':2}
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
    result, excluded_assigned, excluded_stale = [], 0, 0
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
        result.append({key: row.get(key) for key in (
            'id','event_id','alert_type','latitude','longitude','severity','created_at',
            'location_name','location_source','is_demo','evidence_available')})
    return result, excluded_assigned, excluded_stale


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
        coords, alerts, summary, details = [], {}, [], []
        metres, seconds = 0.0, 0.0
        for index, leg in enumerate(legs):
            coords.extend(leg['geometry']['coordinates'] if not coords else leg['geometry']['coordinates'][1:])
            for item in leg['matches']:
                if item['id'] not in alerts:
                    alerts[item['id']] = dict(item, along_route_m=round(item['along_route_m']+metres))
            names = [row.get('summary','') for row in leg.get('legs',[]) if row.get('summary')]
            summary.extend(names)
            details.append(dict(from_label=points[index].label or f'Point {index+1}',
                to_label=points[index+1].label or f'Point {index+2}', distance_km=round(leg['distance']/1000,2),
                duration_minutes=round(leg['duration']/60,1), roads='; '.join(names),
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
    reports, excluded_assigned, excluded_stale = active_reports(db,payload.include_assigned)
    choices, warnings = [], []
    for a,b in zip(points,points[1:]):
        choices.append([score_leg(route,reports) for route in road_routes([a,b])])
    # Try two real-road detours around the largest avoidable hazard. No invented polylines.
    targets = []
    for leg_index, options in enumerate(choices):
        fastest_leg = min(options,key=lambda row:row['duration'])
        for hazard in fastest_leg['matches']:
            point = [hazard['longitude'],hazard['latitude']]
            if hazard['risk_points'] > 0 and min(distance(point,[p.longitude,p.latitude]) for p in points)>300:
                targets.append((hazard['risk_points'],leg_index,fastest_leg,hazard))
    if targets:
        _,index,leg,hazard = max(targets,key=lambda entry:entry[0])
        a,b = leg['geometry']['coordinates'][hazard['_segment']:hazard['_segment']+2]
        scale = cos(radians(hazard['latitude']))
        dx,dy = (b[0]-a[0])*METRES*scale,(b[1]-a[1])*METRES
        length = hypot(dx,dy)
        if length:
            for sign in (-1,1):
                via = JourneyPoint(latitude=hazard['latitude']+sign*dx/length*700/METRES,
                    longitude=hazard['longitude']-sign*dy/length*700/(METRES*scale))
                try:
                    route = road_routes([points[index],via,points[index+1]],alternatives=False)[0]
                    choices[index].append(score_leg(route,reports))
                except HTTPException:
                    warnings.append('One detour could not be calculated; available road routes were still compared.')
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
    if recommended['high_priority_count']:
        warnings.append('The recommended route still passes near high-priority reports. Review their locations before travelling.')
    if len(candidates)==1:
        warnings.append('The road provider returned only one distinct route for these points.')
    if payload.include_assigned:
        warnings.append('Assigned map positions are included for route comparison; their recording locations are unverified.')
    if not reports:
        warnings.append('No eligible active reports are available. This does not confirm that the roads are clear.')
    all_matches = {item['id']: item for row in selected for item in row['issues']}
    return dict(routes=selected,recommended_route_id=recommended['id'],points=[p.model_dump() for p in points],
        issues=list(all_matches.values()), generated_at=datetime.now(timezone.utc).isoformat(),
        preference=payload.preference, max_extra_minutes=payload.max_extra_minutes,
        eligible_reports=len(reports), excluded_assigned_count=excluded_assigned, excluded_stale_count=excluded_stale,
        includes_assigned=payload.include_assigned, compared_routes=len(candidates), warnings=list(dict.fromkeys(warnings)),
        eta_basis='Road-network driving estimate plus planned stop time. Live traffic is not connected.',
        hazard_basis='Nearby active reports within 80–180 m of the route; adjacent roads may be included.',
        attribution='OpenStreetMap contributors · OSRM / FOSSGIS',
        # Compatibility for callers of the previous route endpoint.
        route=[{'latitude':p[1],'longitude':p[0]} for p in recommended['geometry']['coordinates']],
        distance_km=recommended['distance_km'], duration_minutes=recommended['duration_minutes'])
