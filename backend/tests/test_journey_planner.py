"""Road provider fixtures test route decisions, not road safety or model accuracy."""
from copy import deepcopy
from app.core.government_auth import create_government_token
from datetime import datetime, timedelta, timezone

import httpx
import pytest
from fastapi import HTTPException
from test_accident_evidence import system
from app.schemas.journey import JourneyPoint
from app.services import journey_service as journey, map_provider as provider


A = {'latitude': 13.0, 'longitude': 77.60, 'label': 'Pickup'}
B = {'latitude': 13.0, 'longitude': 77.64, 'label': 'Drop-off'}
PAYLOAD = {'origin': A, 'destination': B}


def road(coordinates, minutes=10, metres=4500):
    return {'geometry': {'type': 'LineString', 'coordinates': coordinates},
            'duration': minutes * 60, 'distance': metres, 'legs': [{'summary': 'Test road'}]}


FAST = road([[77.60, 13], [77.64, 13]])
LOWER = road([[77.60, 13], [77.60, 13.01], [77.64, 13.01], [77.64, 13]], 16, 6700)


@pytest.fixture
def roads(monkeypatch):
    calls = []
    def fetch(points, alternatives=True):
        calls.append(points)
        return deepcopy([FAST, LOWER] if len(points) == 2 else [LOWER])
    monkeypatch.setattr(journey, 'road_routes', fetch)
    return calls


def event(client, kind='accident', assigned=False, hours_old=0, **kwargs):
    response = client.post('/api/v1/events', headers={'Authorization':'Bearer '+create_government_token()}, json={
        'event_type': kind, 'latitude': 13, 'longitude': 77.62, 'severity': 'high',
        'timestamp': (datetime.now(timezone.utc) - timedelta(hours=hours_old)).isoformat(),
        'metadata': {'is_demo': assigned, 'location_source': 'simulated' if assigned else 'camera_gps'},
        **kwargs})
    assert response.status_code == 200, response.text
    return response.json()


def plan(client, **kwargs):
    response = client.post('/api/v1/user/route', json={**PAYLOAD, **kwargs})
    assert response.status_code == 200, response.text
    data = response.json()
    selected = next(route for route in data['routes'] if route['recommended'])
    return data, selected


def test_projects_hazard_onto_middle_of_road_segment():
    separation, progress, index = journey.nearest_on_path([77.62, 13.0001], FAST['geometry']['coordinates'])
    assert 10 < separation < 12 and 2100 < progress < 2200 and index == 0


@pytest.mark.parametrize('kind', ['accident', 'waterlogging', 'damaged_road', 'pothole', 'congestion', 'bottleneck'])
def test_balanced_route_reduces_hazards_and_shows_both_alternatives(system, roads, kind):
    client = system[0]
    event(client, kind)
    data, selected = plan(client)
    assert selected['duration_minutes'] == 16 and selected['hazard_count'] == 0
    assert selected['extra_minutes'] == 6 and selected['avoided_hazards'] == 1
    fastest = next(route for route in data['routes'] if 'Fastest' in route['roles'])
    assert fastest['hazard_count'] == 1 and fastest['duration_minutes'] == 10
    assert fastest['issues'][0]['along_route_m'] > 2000
    assert '_segment' not in fastest['issues'][0]
    assert data['compared_routes'] == 2  # Duplicate detours collapse to one road geometry.
    assert len(roads) == 3 and len(roads[-1]) == 3


def test_time_limit_and_fastest_preference_are_respected(system, roads):
    client = system[0]
    event(client)
    data, selected = plan(client, max_extra_minutes=2)
    assert selected['duration_minutes'] == 10 and selected['high_priority_count'] == 1
    assert any('high-priority' in warning for warning in data['warnings'])
    assert all(route['extra_minutes'] <= 2 for route in data['routes'])
    _, selected = plan(client, preference='fastest')
    assert selected['duration_minutes'] == 10
    _, selected = plan(client, preference='lower_risk')
    assert selected['duration_minutes'] == 16


def test_no_helmet_is_informational_and_private_plate_stays_private(system, roads):
    client = system[0]
    event(client, 'helmet_violation', registration_number='KA01AB1234')
    data, selected = plan(client)
    assert selected['duration_minutes'] == 10 and selected['hazard_count'] == 0
    assert selected['report_count'] == 1 and not selected['issues'][0]['affects_ranking']
    assert 'KA01AB1234' not in str(data) and 'plate_matches' not in str(data)
    assert len(roads) == 1


def test_assigned_points_require_explicit_inclusion(system, roads):
    client = system[0]
    event(client, assigned=True)
    data, selected = plan(client)
    assert data['excluded_assigned_count'] == 1 and not data['issues']
    assert selected['duration_minutes'] == 10
    data, selected = plan(client, include_assigned=True)
    assert selected['duration_minutes'] == 16 and data['issues'][0]['is_demo']
    assert any('unverified' in note for note in data['warnings'])


def test_stale_transient_reports_and_resolved_issues_stop_affecting_routes(system, roads):
    client, headers = system[:2]
    event(client, 'accident', hours_old=7)
    event(client, 'pothole', hours_old=48)
    data, selected = plan(client)
    assert data['excluded_stale_count'] == 1 and selected['duration_minutes'] == 16
    issue_id = next(row['id'] for row in client.get('/api/v1/government/issues', headers=headers).json() if row['event_type'] == 'pothole')
    response = client.patch(f'/api/v1/government/issues/{issue_id}/status', headers=headers, json={'status': 'resolved', 'note': 'Repair completed'})
    assert response.status_code == 200, response.text
    data, selected = plan(client)
    assert selected['duration_minutes'] == 10 and not data['issues']


def test_ordered_stops_and_dwell_time(system, monkeypatch):
    client = system[0]
    calls = []
    def fetch(points, alternatives=True):
        calls.append([(p.longitude, p.latitude) for p in points])
        return [road([[p.longitude, p.latitude] for p in points], minutes=4, metres=1800)]
    monkeypatch.setattr(journey, 'road_routes', fetch)
    stops = [{'latitude': 13.01, 'longitude': 77.61, 'label': 'Stop one', 'dwell_minutes': 5},
             {'latitude': 13.01, 'longitude': 77.63, 'label': 'Stop two', 'dwell_minutes': 2}]
    data, selected = plan(client, stops=stops)
    assert calls == [[(77.60, 13), (77.61, 13.01)], [(77.61, 13.01), (77.63, 13.01)], [(77.63, 13.01), (77.64, 13)]]
    assert selected['driving_minutes'] == 12 and selected['stop_minutes'] == 7 and selected['duration_minutes'] == 19
    assert [leg['stop_minutes'] for leg in selected['legs']] == [5, 2, 0]
    assert selected['geometry']['coordinates'] == [[77.60, 13], [77.61, 13.01], [77.63, 13.01], [77.64, 13]]
    assert any('one distinct route' in note for note in data['warnings'])


def test_same_report_is_counted_once_across_adjacent_legs(system, monkeypatch):
    client = system[0]
    event(client, 'pothole')
    monkeypatch.setattr(journey, 'road_routes', lambda points, **_: [road([[p.longitude, p.latitude] for p in points])])
    _, selected = plan(client, stops=[{'latitude': 13, 'longitude': 77.62}])
    assert selected['report_count'] == selected['hazard_count'] == 1


@pytest.mark.parametrize('change', [
    {'destination': A}, {'origin': {**A, 'latitude': 91}}, {'origin': {**A, 'latitude': 'NaN'}},
    {'destination': {**B, 'longitude': 78.99}}, {'stops': [A] * 4},
    {'stops': [{**B, 'dwell_minutes': -1}]}, {'preference': 'teleport'}, {'max_extra_minutes': -1}])
def test_invalid_journeys_are_rejected_before_provider_call(system, roads, change):
    response = system[0].post('/api/v1/user/route', json={**PAYLOAD, **change})
    assert response.status_code == 422 and not roads


def test_provider_failure_returns_error_without_inventing_route(system, monkeypatch):
    def fail(*args, **kwargs):
        raise HTTPException(503, 'Map service is unavailable.')
    monkeypatch.setattr(journey, 'road_routes', fail)
    response = system[0].post('/api/v1/user/route', json=PAYLOAD)
    assert response.status_code == 503 and 'route' not in response.json()


def test_failed_detours_keep_available_routes(system, monkeypatch):
    client = system[0]
    event(client)
    def fetch(points, alternatives=True):
        if len(points) == 3:
            raise HTTPException(422, 'No road')
        return [deepcopy(FAST)]
    monkeypatch.setattr(journey, 'road_routes', fetch)
    data, selected = plan(client)
    assert selected['hazard_count'] == 1
    assert any('detour could not' in note for note in data['warnings'])


def test_provider_cache_and_bad_geometry(monkeypatch):
    calls = []
    def get(url, **kwargs):
        calls.append(url)
        return httpx.Response(200, json={'code': 'Ok', 'routes': [deepcopy(FAST)]}, request=httpx.Request('GET', url))
    monkeypatch.setattr(provider.httpx, 'get', get)
    from collections import OrderedDict
    monkeypatch.setattr(provider, '_cache', OrderedDict())
    monkeypatch.setattr(provider, 'sleep', lambda _: None)
    points = [JourneyPoint(**A), JourneyPoint(**B)]
    assert provider.road_routes(points)[0]['distance'] == 4500
    provider.road_routes(points)
    assert len(calls) == 1
    monkeypatch.setattr(provider, '_fetch', lambda *args: {'code': 'Ok', 'routes': [road([[77.6, 13], [999, 13]])]})
    with pytest.raises(HTTPException) as error:
        provider.road_routes(points)
    assert error.value.status_code == 502


def test_blank_place_query_is_rejected_without_network(system, monkeypatch):
    monkeypatch.setattr(provider, '_fetch', lambda *args: pytest.fail('Must validate before network'))
    assert system[0].get('/api/v1/user/places', params={'q': '   '}).status_code == 422
