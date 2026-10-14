"""Bounded, cached requests to configurable road-routing and place services."""
from collections import OrderedDict
from copy import deepcopy
from math import isfinite
from threading import Lock
from time import monotonic, sleep
import httpx
from fastapi import HTTPException
from app.core.config import settings

_locks = {'route': Lock(), 'places': Lock()}
_last_request = {'route': 0.0, 'places': 0.0}
_cache = OrderedDict()
_cache_lock = Lock()


def _fetch(kind, url, params, ttl):
    key = (kind, url, tuple(sorted(params.items())))
    with _cache_lock:
        cached = _cache.get(key)
        if cached and cached[0] > monotonic():
            return deepcopy(cached[1])
    lock = _locks[kind]
    if not lock.acquire(timeout=5):
        raise HTTPException(503, 'Map service is busy. Please try again shortly.')
    try:
        with _cache_lock:
            cached = _cache.get(key)
            if cached and cached[0] > monotonic():
                return deepcopy(cached[1])
        sleep(max(0, 1.05 - (monotonic() - _last_request[kind])))
        _last_request[kind] = monotonic()
        try:
            response = httpx.get(url, params=params, timeout=15,
                headers={'User-Agent': settings.MAP_USER_AGENT, 'Accept': 'application/json'})
            if response.status_code == 429:
                raise HTTPException(503, 'Map provider is busy. Try again in a moment.')
            if response.status_code in (401, 403) and kind == 'route' and settings.ROUTING_PROVIDER == 'tomtom':
                raise HTTPException(503, 'TomTom rejected the routing request. Check the API key and Routing API access.')
            if kind == 'route' and response.status_code == 400:
                raise HTTPException(422, 'A point could not be connected to a drivable road. Move the pin closer to a road.')
            response.raise_for_status()
            data = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            raise HTTPException(503, 'Map service is unavailable. Check the connection and try again.') from exc
        with _cache_lock:
            _cache[key] = (monotonic() + ttl, data)
            _cache.move_to_end(key)
            while len(_cache) > 128:
                _cache.popitem(last=False)
        return deepcopy(data)
    finally:
        lock.release()


def road_routes(points, alternatives=True):
    if settings.ROUTING_PROVIDER == 'tomtom':
        return _tomtom_routes(points, alternatives)

    coordinates = ';'.join(f'{point.longitude:.6f},{point.latitude:.6f}' for point in points)
    url = settings.ROUTING_BASE_URL.rstrip('/') + '/route/v1/driving/' + coordinates
    data = _fetch('route', url, dict(overview='full', geometries='geojson',
        alternatives='true' if alternatives else 'false', steps='true',
        radiuses=';'.join(['250'] * len(points))), 300)
    if not isinstance(data, dict) or data.get('code') != 'Ok' or not data.get('routes'):
        raise HTTPException(422, 'No driving route connects these points. Choose another road or stop.')
    result = []
    for route in data['routes'][:3]:
        try:
            coords = route['geometry']['coordinates']
            if len(coords) < 2 or len(coords) > 25000:
                raise ValueError('Invalid geometry')
            if not all(len(p) == 2 and all(isfinite(v) for v in p) and abs(p[0]) <= 180 and abs(p[1]) <= 90 for p in coords):
                raise ValueError('Invalid coordinates')
            if not all(isfinite(route[k]) and route[k] >= 0 for k in ('duration', 'distance')):
                raise ValueError('Invalid route totals')
            route['waypoints'] = data.get('waypoints', [])
            result.append(route)
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(502, 'Map provider returned an incomplete route. Please retry.') from exc
    return result


def _tomtom_routes(points, alternatives):
    if not settings.TOMTOM_API_KEY.strip():
        raise HTTPException(503, 'TomTom routing is selected, but TOMTOM_API_KEY is not configured.')

    locations = ':'.join(f'{point.latitude:.6f},{point.longitude:.6f}' for point in points)
    url = f'https://api.tomtom.com/routing/1/calculateRoute/{locations}/json'
    params = {
        'key': settings.TOMTOM_API_KEY.strip(),
        'traffic': 'true',
        'computeTravelTimeFor': 'all',
        'routeType': 'fastest',
        'routeRepresentation': 'polyline',
        'sectionType': 'traffic',
        'maxAlternatives': 2 if alternatives and len(points) == 2 else 0,
    }
    data = _fetch('route', url, params, 60)
    if not isinstance(data, dict) or not data.get('routes'):
        raise HTTPException(422, 'TomTom could not find a drivable route for these points. Choose another road or stop.')

    result = []
    for route in data['routes'][:3]:
        try:
            route_legs = route['legs']
            coordinates = []
            normalized_legs = []
            for leg in route_legs:
                summary = leg['summary']
                leg_coordinates = [[point['longitude'], point['latitude']] for point in leg['points']]
                if len(leg_coordinates) < 2:
                    raise ValueError('Invalid leg geometry')
                coordinates.extend(leg_coordinates if not coordinates else leg_coordinates[1:])
                normalized_legs.append({
                    'summary': '',
                    'distance': summary['lengthInMeters'],
                    'duration': summary['travelTimeInSeconds'],
                    'traffic_delay_seconds': summary.get('trafficDelayInSeconds'),
                    'no_traffic_duration_seconds': summary.get('noTrafficTravelTimeInSeconds'),
                })

            summary = route['summary']
            distance = summary.get('lengthInMeters', sum(leg['distance'] for leg in normalized_legs))
            duration = summary.get('travelTimeInSeconds', sum(leg['duration'] for leg in normalized_legs))
            if len(coordinates) < 2 or len(coordinates) > 25000:
                raise ValueError('Invalid geometry')
            if not all(len(point) == 2 and all(isfinite(value) for value in point)
                       and abs(point[0]) <= 180 and abs(point[1]) <= 90 for point in coordinates):
                raise ValueError('Invalid coordinates')
            if not all(isfinite(value) and value >= 0 for value in (distance, duration)):
                raise ValueError('Invalid route totals')

            traffic_sections = []
            sections = route.get('sections', [])
            for section in (sections[:200] if isinstance(sections, list) else []):
                if not isinstance(section, dict):
                    continue
                if section.get('sectionType') != 'TRAFFIC':
                    continue
                start = section.get('startPointIndex')
                end = section.get('endPointIndex')
                if not (isinstance(start, int) and isinstance(end, int)
                        and 0 <= start < end < len(coordinates)):
                    continue
                delay = section.get('delayInSeconds')
                if not isinstance(delay, (int, float)) or isinstance(delay, bool) or not isfinite(delay) or delay < 0:
                    delay = None
                category = section.get('simpleCategory', 'OTHER')
                if not isinstance(category, str):
                    category = 'OTHER'
                traffic_sections.append({
                    'category': category[:40],
                    'delay_seconds': delay,
                    'magnitude': section.get('magnitudeOfDelay') if isinstance(section.get('magnitudeOfDelay'), int) else None,
                    'coordinates': coordinates[start:end + 1],
                })

            traffic_delay = summary.get('trafficDelayInSeconds')
            if not isinstance(traffic_delay, (int, float)) or isinstance(traffic_delay, bool) or not isfinite(traffic_delay) or traffic_delay < 0:
                traffic_delay = None

            result.append({
                'geometry': {'type': 'LineString', 'coordinates': coordinates},
                'distance': distance,
                'duration': duration,
                'traffic_aware': True,
                'traffic_delay_seconds': traffic_delay,
                'no_traffic_duration_seconds': summary.get('noTrafficTravelTimeInSeconds'),
                'traffic_sections': traffic_sections,
                'legs': normalized_legs,
            })
        except (KeyError, TypeError, ValueError) as exc:
            raise HTTPException(502, 'TomTom returned an incomplete route. Please retry.') from exc
    return result


def search_places(query):
    # Explicit searches only; Bengaluru bias, cached and rate-limited per process.
    if not 3 <= len(query.strip()) <= 160:
        raise HTTPException(422, 'Enter a place name of 3–160 characters.')
    data = _fetch('places', settings.GEOCODING_BASE_URL.rstrip('/') + '/api/',
        dict(q=query.strip(), limit=6, lang='en', lat=12.9716, lon=77.5946), 86400)
    result = []
    for feature in data.get('features', []) if isinstance(data, dict) else []:
        try:
            lon, lat = feature['geometry']['coordinates']
            if not (isfinite(lat) and isfinite(lon) and abs(lat) <= 90 and abs(lon) <= 180):
                continue
            props = feature['properties']
            pieces = [props.get(key) for key in ('name', 'street', 'city', 'district', 'state', 'country')]
            name = ', '.join(dict.fromkeys(str(piece) for piece in pieces if piece))
            result.append({'label': name or f'{lat:.5f}, {lon:.5f}', 'latitude': lat, 'longitude': lon})
        except (KeyError, ValueError, TypeError):
            continue
    return {'places': result, 'attribution': 'OpenStreetMap contributors · Photon'}
