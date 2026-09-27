import json
from copy import deepcopy
from datetime import datetime, timezone

import pytest
from test_accident_evidence import system
from app.services.helmet_plates import associate_rows
from app.services.alert_service import ensure_event_alert
from app.models.event import Event
from app.models.alert import Alert


def test_helmet_upload_always_selects_plate_ocr():
    from app.api.routes.video_analysis import PROFILES
    assert set(PROFILES['helmet']) == {'helmet', 'number_plate'}
    assert {'helmet', 'number_plate'} <= set(PROFILES['motorcycle'])


def test_demo_ingestion_creates_no_enforcement_and_preserves_priority(system):
    from app.models.violation import Violation
    client, headers, sessions, item, folder = system
    payload = {'event_type': 'helmet_violation', 'latitude': 13, 'longitude': 77.6,
               'severity': 'high', 'metadata': {'is_demo': True}}
    response = client.post('/api/v1/events', headers=headers, json=payload)
    assert response.status_code == 200 and response.json()['status'] == 'demo'
    with sessions() as db:
        assert db.query(Violation).count() == 0
        assert db.query(Alert).one().severity == 'high'
    assert client.get('/api/v1/user/alerts').json()[0]['is_demo']


def rider_row(index=0):
    return {'frame_index': index, 'timestamp_seconds': index / 10, 'detections': [
        {'label': 'motorcycle', 'track_id': 1, 'bbox_xyxy': [10, 20, 60, 60]},
        {'label': 'without_helmet', 'track_id': 1, 'confidence': .9, 'bbox_xyxy': [20, 5, 30, 18]},
        {'label': 'number_plate', 'confidence': .8, 'text': 'KA01AB1234', 'ocr_confidence': .92, 'bbox_xyxy': [25, 45, 40, 55]},
    ]}


def test_plate_requires_same_frame_and_unique_same_motorcycle():
    row = rider_row()
    match, = associate_rows([row])
    assert match['plate_text'] == 'KA01AB1234' and match['verified'] is False
    assert match['reading_status'] == 'uncertain'
    assert associate_rows([rider_row(i) for i in range(3)])[0]['reading_status'] == 'repeated_ocr_candidate'
    ambiguous = deepcopy(row)
    ambiguous['detections'].append({'label': 'motorcycle', 'track_id': 2, 'bbox_xyxy': [10, 20, 60, 60]})
    assert associate_rows([ambiguous]) == []
    unrelated = deepcopy(row)
    unrelated['detections'][-1]['bbox_xyxy'] = [80, 45, 95, 55]
    assert associate_rows([unrelated]) == []
    helmeted = deepcopy(row)
    helmeted['detections'][1]['label'] = 'with_helmet'
    assert associate_rows([helmeted]) == []
    before, after = deepcopy(row), rider_row(1)
    before['detections'].pop()
    after['detections'].pop(1)
    assert associate_rows([before, after]) == []


def test_no_helmet_alert_has_private_plate_evidence_and_dismissal(system):
    client, headers, sessions, item, folder = system
    (folder / 'detections.jsonl').write_text(''.join(json.dumps(rider_row(i)) + '\n' for i in range(6)))
    payload = {'segment_id': 'helmet_00000000', 'latitude': 13.0123, 'longitude': 77.6123,
               'occurred_at': datetime.now(timezone.utc).isoformat(), 'location_name': 'Demo junction', 'demo': True}
    endpoint = f'/api/v1/government/analysis-results/{item["id"]}/incidents'
    response = client.post(endpoint, headers=headers, json=payload)
    assert response.status_code == 200, response.text
    event_id = response.json()['incident']['id']
    assert client.post(endpoint, headers=headers, json=payload).json()['duplicate'] is True
    private = client.get('/api/v1/government/alerts', headers=headers).json()
    assert len(private) == 1
    alert = private[0]
    assert alert['event_id'] == event_id and alert['alert_type'] == 'helmet_violation'
    assert alert['latitude'] == payload['latitude'] and alert['longitude'] == payload['longitude']
    assert alert['location_source'] == 'simulated' and alert['evidence_available']
    assert alert['plate_matches'][0]['plate_text'] == 'KA01AB1234'
    assert alert['plate_matches'][0]['verified'] is False
    public = client.get('/api/v1/user/alerts').json()[0]
    assert public['is_demo'] is True and 'plate_matches' not in public and 'reported_registration' not in public
    public_metadata = json.loads(client.get('/api/v1/user/map-events').json()[0]['event_metadata'])
    assert 'helmet_plate_matches' not in public_metadata
    assert 'KA01AB1234' not in client.get('/api/v1/events/',headers=headers).text
    assert client.get('/api/v1/user/alerts?include_demo=false').json() == []
    evidence = client.get(f'/api/v1/government/analysis-results/incidents/{event_id}', headers=headers).json()
    assert any(set(f['labels']) == {'without_helmet', 'number_plate'} for f in evidence['frames'])
    route = f'/api/v1/government/alerts/{alert["id"]}'
    assert client.patch(route, json={'status': 'dismissed'}).status_code == 401
    assert client.patch(route, headers=headers, json={'status': 'dismissed'}).status_code == 200
    with sessions() as db:
        ensure_event_alert(db, db.get(Event, event_id))
        db.commit()
        assert db.query(Alert).count() == 1
    assert client.get('/api/v1/user/alerts').json() == []
    client.patch(route, headers=headers, json={'status': 'active'})
    assert len(client.get('/api/v1/user/alerts').json()) == 1


@pytest.mark.parametrize('kind, expected', [('pothole', 'pothole'), ('waterlogging', 'waterlogging'),
    ('damaged_road', 'road_damage'), ('accident', 'accident'), ('helmet_violation', 'helmet_violation'),
    ('traffic_violation', 'traffic_violation'), ('congestion', 'congestion'), ('bottleneck', 'bottleneck')])
def test_main_issue_ingestion_preserves_camera_coordinates(system, kind, expected):
    client, headers, sessions, item, folder = system
    payload = {'event_type': kind, 'latitude': 13.06, 'longitude': 77.61,
               'timestamp': '2026-09-27T10:00:00+05:30',
               'metadata': {'location_source': 'camera_gps', 'location_name': 'Camera 2'},
               'registration_number': 'KA01AB1234' if kind == 'helmet_violation' else None}
    result = client.post('/api/v1/events', headers=headers, json=payload)
    assert result.status_code == 200, result.text
    alerts = client.get('/api/v1/government/alerts', headers=headers).json()
    assert len(alerts) == 1 and alerts[0]['alert_type'] == expected
    assert alerts[0]['location_source'] == 'camera_gps' and not alerts[0]['is_demo']
    assert alerts[0]['latitude'] == 13.06 and alerts[0]['longitude'] == 77.61
    assert alerts[0]['created_at'] == '2026-09-27T04:30:00+00:00'
    assert client.post('/api/v1/events', headers=headers, json={**payload, 'latitude': 91}).status_code == 422
    nearby = client.get('/api/v1/user/nearby-alerts?latitude=13.06&longitude=77.61').json()
    assert len(nearby) == 1 and nearby[0]['distance_km'] == 0
