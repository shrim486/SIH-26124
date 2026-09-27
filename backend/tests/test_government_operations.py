import json
from datetime import datetime, timezone, timedelta
import pytest
from test_accident_evidence import system, publication
from app.models.event import Event
from app.models.violation import Violation
from app.models.road_issue import RoadIssue
from app.models.alert import Alert
from app.services.alert_service import ensure_event_alert


@pytest.mark.parametrize('kind,group', [('pothole','road'), ('waterlogging','road'),
    ('damaged_road','road'), ('accident','accidents'), ('helmet','violations'), ('traffic_violation','violations')])
def test_issue_workflow_clears_and_restores_same_public_alert(system, kind, group):
    client, headers, sessions, item, folder = system
    with sessions() as db:
        event = Event(event_type=kind,latitude=13.05,longitude=77.61,status='demo',
            event_metadata=json.dumps({'is_demo':True, 'detected_labels':['without_helmet']}))
        db.add(event); db.flush(); ensure_event_alert(db,event); db.commit(); event_id=event.id
    issues = client.get(f'/api/v1/government/issues?category={group}',headers=headers).json()
    assert len(issues) == 1 and issues[0]['id'] == event_id and issues[0]['status'] == 'open'
    endpoint = f'/api/v1/government/issues/{event_id}/status'
    assert client.patch(endpoint,json={'status':'resolved'}).status_code == 401
    assert client.patch(endpoint,headers=headers,json={'status':'bad'}).status_code == 422
    alert = client.get('/api/v1/user/alerts').json()[0]
    for status in ['in_progress','resolved','resolved','open','closed','open']:
        response = client.patch(endpoint,headers=headers,json={'status':status,'note':'Inspection test'})
        assert response.status_code == 200, response.text
        assert response.json()['status'] == status and response.json()['is_demo'] is True
        public = client.get('/api/v1/user/alerts').json()
        assert len(public) == (0 if status in {'resolved','closed'} else 1)
        if public:
            assert public[0]['id'] == alert['id'] and public[0]['event_id'] == event_id
        else:
            assert client.patch(f'/api/v1/government/alerts/{alert["id"]}',headers=headers,json={'status':'active'}).status_code == 409
        pin = client.get('/api/v1/user/map-events').json()[0]
        assert pin['status'] == status and pin['is_demo'] is True
        assert (pin['latitude'],pin['longitude']) == (13.05,77.61)
        statistics = client.get('/api/v1/user/dashboard').json()['statistics']
        assert statistics['resolved_issues'] == int(status in {'resolved','closed'})
        assert statistics['demo_issues'] == 1
        with sessions() as db:
            ensure_event_alert(db,db.get(Event,event_id)); db.commit()
            assert db.query(Alert).count() == 1
            assert db.query(Violation).count() == 0
            assert db.query(RoadIssue).count() == 0
    assert client.get('/api/v1/user/alerts?include_demo=false').json() == []
    history = client.get(f'/api/v1/government/issues/{event_id}/history',headers=headers).json()
    assert len(history) == 5  # Retrying resolved is idempotent.
    assert history[0]['note'] == 'Inspection test'


def test_curated_catalog_and_protected_video_survive_resolution(system):
    client, headers, sessions, item, folder = system
    endpoint = f'/api/v1/government/analysis-results/{item["id"]}/incidents'
    event_id = client.post(endpoint,headers=headers,json=publication(item)).json()['incident']['id']
    with sessions() as db:
        for kind in ['number_plate','traffic_sign','zebra_crossing','helmet']:
            db.add(Event(event_type=kind,latitude=13,longitude=77,status='demo',
                         event_metadata=json.dumps({'is_demo':True,'detected_labels':['with_helmet']})))
        db.commit()
    assert client.get('/api/v1/government/issues').status_code == 401
    rows = client.get('/api/v1/government/issues',headers=headers).json()
    assert [row['id'] for row in rows] == [event_id] and rows[0]['evidence_available']
    client.patch(f'/api/v1/government/issues/{event_id}/status',headers=headers,json={'status':'resolved'})
    evidence = f'/api/v1/government/analysis-results/incidents/{event_id}'
    assert client.get(evidence).status_code == 401
    response = client.get(evidence,headers=headers)
    assert response.status_code == 200 and response.json()['frames']
    assert client.get('/api/v1/government/issues?status=open',headers=headers).json() == []
    assert len(client.get('/api/v1/government/issues?status=resolved',headers=headers).json()) == 1


def test_live_report_links_legacy_tables_and_preserves_review_on_repeat(system):
    client, headers, sessions, item, folder = system
    payload = dict(event_type='pothole',latitude=13,longitude=77.6)
    client.post('/api/v1/events', headers=headers,json=payload)
    issue = client.get('/api/v1/government/issues',headers=headers).json()[0]
    endpoint = f'/api/v1/government/issues/{issue["id"]}/status'
    client.patch(endpoint,headers=headers,json={'status':'in_progress'})
    client.post('/api/v1/events', headers=headers,json=payload)
    assert client.get('/api/v1/government/issues',headers=headers).json()[0]['status'] == 'in_progress'
    client.patch(endpoint,headers=headers,json={'status':'resolved'})
    with sessions() as db:
        road = db.query(RoadIssue).one(); road_id = road.id
        assert road.status == 'resolved'
    client.patch(f'/api/v1/government/road-issues/{road_id}/status',headers=headers,json={'status':'open'})
    assert len(client.get('/api/v1/user/alerts').json()) == 1
    client.post('/api/v1/events', headers=headers,json={**payload,'event_type':'helmet_violation','registration_number':'KA01AB1234'})
    violation = client.get('/api/v1/government/issues?category=violations',headers=headers).json()[0]
    with sessions() as db:
        violation_id = db.query(Violation).one().id
    client.patch(f'/api/v1/government/issues/{violation["id"]}/status',headers=headers,json={'status':'closed'})
    with sessions() as db:
        assert db.get(Violation,violation_id).status == 'dismissed'
    client.patch(f'/api/v1/government/violations/{violation_id}/status',headers=headers,json={'status':'pending'})
    assert client.get('/api/v1/government/issues?category=violations',headers=headers).json()[0]['status'] == 'open'


def test_resolved_demo_never_absorbs_real_detection(system):
    client, headers, sessions, item, folder = system
    payload = dict(event_type='pothole',latitude=13,longitude=77.6)
    client.post('/api/v1/events', headers=headers,json={**payload,'metadata':{'is_demo':True}})
    issue = client.get('/api/v1/government/issues',headers=headers).json()[0]
    client.patch(f'/api/v1/government/issues/{issue["id"]}/status',headers=headers,json={'status':'open'})
    client.post('/api/v1/events', headers=headers,json=payload)
    rows = client.get('/api/v1/government/issues',headers=headers).json()
    assert len(rows) == 2 and sum(row['is_demo'] for row in rows) == 1


def test_fleet_registration_camera_health_and_gps_freshness(system):
    client, headers, sessions, item, folder = system
    root = '/api/v1/government/fleet'
    bus = dict(bus_number='ka01-test',route_number='500D',is_active=True)
    assert client.post(root+'/buses',json=bus).status_code == 401
    response = client.post(root+'/buses',headers=headers,json=bus)
    assert response.status_code == 201; bus_id = response.json()['id']
    assert client.post(root+'/buses',headers=headers,json=bus).status_code == 409
    assert client.post(root+'/buses',headers=headers,json={'bus_number':'  '}).status_code == 422
    fleet = client.get(root,headers=headers).json()
    assert fleet['buses'][0]['latitude'] is None and fleet['online_buses'] == 0
    camera = dict(bus_id=bus_id,camera_code='front-test',camera_type='front')
    response = client.post(root+'/cameras',headers=headers,json=camera)
    assert response.status_code == 201
    camera_id = response.json()['id']
    assert client.post(root+'/cameras',headers=headers,json=camera).status_code == 409
    assert client.patch(f'{root}/cameras/{camera_id}',headers=headers,json={'status':'maintenance'}).status_code == 200
    position = dict(latitude=13.02,longitude=77.6,recorded_at=(datetime.now(timezone.utc)-timedelta(minutes=5)).isoformat(),source='device')
    endpoint = f'{root}/buses/{bus_id}/position'
    assert client.post(endpoint,headers=headers,json={**position,'latitude':91}).status_code == 422
    assert client.post(endpoint,headers=headers,json={**position,'recorded_at':'2026-01-01T10:00:00'}).status_code == 422
    assert client.post(endpoint,headers=headers,json={**position,'recorded_at':(datetime.now(timezone.utc)+timedelta(hours=1)).isoformat()}).status_code == 422
    assert client.post(endpoint,headers=headers,json=position).status_code == 200
    assert client.get(root,headers=headers).json()['buses'][0]['connection_status'] == 'stale'
    assert client.post(endpoint,headers=headers,json=position).status_code == 409
    position['recorded_at'] = (datetime.now(timezone.utc)-timedelta(seconds=5)).isoformat()
    position['source'] = 'manual'
    assert client.post(endpoint,headers=headers,json=position).status_code == 200
    assert client.get(root,headers=headers).json()['buses'][0]['connection_status'] == 'manual_location'
    position.update(recorded_at=datetime.now(timezone.utc).isoformat(),source='device')
    assert client.post(endpoint,headers=headers,json=position).status_code == 200
    client.post('/api/v1/events', headers=headers,json=dict(event_type='accident',latitude=13,longitude=77,bus_id=bus_id))
    fleet = client.get(root,headers=headers).json()
    assert fleet['online_buses'] == 1 and fleet['buses'][0]['camera_count'] == 1
    assert fleet['buses'][0]['issue_count'] == 1
    assert len(client.get(f'/api/v1/government/issues?bus_id={bus_id}',headers=headers).json()) == 1
    client.put(root+f'/buses/{bus_id}',headers=headers,json={**bus,'is_active':False})
    assert client.get(root,headers=headers).json()['buses'][0]['connection_status'] == 'inactive'
