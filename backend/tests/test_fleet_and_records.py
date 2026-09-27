import json
import shutil
from datetime import datetime, timedelta, timezone
import cv2
import numpy as np
import pytest
from test_accident_evidence import system, publication
from app.services import alert_service
from app.models.fleet_history import FleetPositionHistory


ROOT = '/api/v1/government/fleet'


def register(client, headers, name='KA01-TEST'):
    result = client.post(ROOT+'/buses', headers=headers, json={'bus_number':name,'route_number':'500D'})
    assert result.status_code == 201, result.text
    return result.json()['id']


def test_portals_share_record_identity_counts_evidence_and_archive(system):
    client, headers, _, item, _ = system
    published = client.post(f'/api/v1/government/analysis-results/{item["id"]}/incidents',headers=headers,json=publication(item))
    assert published.status_code == 200
    event_id = published.json()['incident']['id']
    assert client.get('/api/v1/government/records').status_code == 401
    public = client.get('/api/v1/user/records').json()
    private = client.get('/api/v1/government/records',headers=headers).json()
    assert public['total'] == public['mapped'] == public['with_evidence'] == 1
    assert private['total'] == private['mapped'] == private['with_evidence'] == 1
    assert public['records'][0]['reference'] == f'INC-{event_id:05d}'
    for key in ('id','event_id','reference','latitude','longitude','alert_type','evidence_available'):
        assert public['records'][0][key] == private['records'][0][key]
    assert 'plate_matches' not in public['records'][0] and 'reported_registration' not in public['records'][0]
    client.patch(f'/api/v1/government/issues/{event_id}/status',headers=headers,json={'status':'resolved'})
    for endpoint in ('user','government'):
        assert client.get(f'/api/v1/{endpoint}/records',headers=headers).json()['total'] == 0
        archived = client.get(f'/api/v1/{endpoint}/records?archive=true',headers=headers).json()
        assert archived['total'] == 1 and archived['records'][0]['issue_status'] == 'resolved'
    assert client.get(f'/api/v1/government/analysis-results/incidents/{event_id}',headers=headers).status_code == 200


def test_missing_or_invalid_coordinates_are_counted_without_fake_pins(monkeypatch):
    common = dict(active=True, issue_status='open',event_id=None,evidence_available=False,alert_type='waterlogging')
    rows = [dict(common,id=1,latitude=None,longitude=None),dict(common,id=2,latitude=13,longitude=77.6),dict(common,id=3,latitude=99,longitude=77.6),dict(common,id=4,latitude=13,longitude=77.6,alert_type='number_plate')]
    monkeypatch.setattr(alert_service,'list_alerts',lambda *args,**kwargs:rows)
    data = alert_service.records_payload(None)
    assert data['total'] == 3 and data['mapped'] == 1 and data['missing_location'] == 2
    assert data['records'][0]['latitude'] is None and data['records'][0]['reference'] == 'ALT-00001'


def test_position_history_order_bounds_auth_and_rejected_updates(system):
    client, headers, sessions, _, _ = system
    bus_id = register(client,headers)
    now = datetime.now(timezone.utc)
    for minutes, source in [(40,'device'),(30,'device'),(20,'manual'),(10,'device')]:
        payload=dict(latitude=13+minutes/10000,longitude=77.6,recorded_at=(now-timedelta(minutes=minutes)).isoformat(),source=source)
        assert client.post(f'{ROOT}/buses/{bus_id}/position',headers=headers,json=payload).status_code == 200
    assert client.post(f'{ROOT}/buses/{bus_id}/position',headers=headers,json=payload).status_code == 409
    path=f'{ROOT}/buses/{bus_id}/history'
    assert client.get(path).status_code == 401
    history=client.get(path+'?hours=1&limit=3',headers=headers).json()
    assert history['truncated'] and len(history['points'])==3
    assert [p['source'] for p in history['points']] == ['device','manual','device']
    assert [p['recorded_at'] for p in history['points']] == sorted(p['recorded_at'] for p in history['points'])
    with sessions() as db:
        assert db.query(FleetPositionHistory).count()==4
    assert client.get(path+'?limit=3001',headers=headers).status_code==422
    assert client.get(ROOT+'/buses/999/history',headers=headers).status_code==404


def test_camera_health_requires_recent_actual_frame_reports(system):
    client, headers = system[:2]
    bus_id=register(client,headers)
    camera=client.post(ROOT+'/cameras',headers=headers,json={'bus_id':bus_id,'camera_code':'FRONT-1'}).json()
    camera_id=camera['id']
    fleet=client.get(ROOT,headers=headers).json()
    assert fleet['cameras'][0]['health']=='no_telemetry' and fleet['cameras_receiving_frames']==0
    path=f'{ROOT}/cameras/{camera_id}/heartbeat'
    now=datetime.now(timezone.utc)
    old=(now-timedelta(minutes=4)).isoformat()
    assert client.post(path,json={'recorded_at':old,'last_frame_at':old}).status_code==401
    assert client.post(path,headers=headers,json={'recorded_at':old,'last_frame_at':old}).status_code==200
    assert client.get(ROOT,headers=headers).json()['cameras'][0]['health']=='stale'
    recorded=(now-timedelta(seconds=4)).isoformat()
    assert client.post(path,headers=headers,json={'recorded_at':recorded,'last_frame_at':old}).status_code==200
    assert client.get(ROOT,headers=headers).json()['cameras'][0]['health']=='no_recent_frames'
    recorded=(now-timedelta(seconds=2)).isoformat()
    assert client.post(path,headers=headers,json={'recorded_at':recorded,'last_frame_at':recorded}).status_code==200
    fleet=client.get(ROOT,headers=headers).json()
    assert fleet['cameras_receiving_frames']==1 and fleet['online_buses']==0
    assert client.post(path,headers=headers,json={'recorded_at':recorded}).status_code==409
    assert client.post(path,headers=headers,json={'recorded_at':now.isoformat(),'state':'error','message':'Capture failed'}).status_code==200
    assert client.get(ROOT,headers=headers).json()['cameras'][0]['health']=='error'
    assert client.post(path,headers=headers,json={'recorded_at':now.isoformat(),'last_frame_at':(now+timedelta(seconds=10)).isoformat()}).status_code==422
    assert client.post(path,headers=headers,json={'recorded_at':'2026-01-01T10:00:00'}).status_code==422


def test_camera_edits_preserve_vehicle_and_known_camera_infers_bus(system):
    client, headers=system[:2]
    first,second=register(client,headers),register(client,headers,'KA02-TEST')
    camera_id=client.post(ROOT+'/cameras',headers=headers,json={'bus_id':first,'camera_code':'front'}).json()['id']
    change={'bus_id':first,'camera_code':'front-updated','camera_type':'rear'}
    assert client.put(f'{ROOT}/cameras/{camera_id}',headers=headers,json=change).status_code==200
    assert client.put(f'{ROOT}/cameras/{camera_id}',headers=headers,json={**change,'bus_id':second}).status_code==422
    payload={'event_type':'pothole','latitude':13,'longitude':77.6,'camera_id':camera_id}
    response=client.post('/api/v1/events', headers=headers,json=payload)
    assert response.status_code==200
    assert client.get(f'/api/v1/government/issues?bus_id={first}',headers=headers).json()[0]['camera_id']==camera_id
    assert client.post('/api/v1/events', headers=headers,json={**payload,'bus_id':second}).status_code==422
    client.post('/api/v1/events', headers=headers,json={**payload,'camera_id':None,'bus_id':second})
    fleet=client.get(ROOT,headers=headers).json()
    assert [bus['issue_count'] for bus in fleet['buses']]==[1,1]
    assert len(client.get(f'/api/v1/government/issues?bus_id={second}',headers=headers).json())==1


def test_reused_waterlogging_footage_is_rejected_and_distinct_videos_link_separately(system):
    client,headers,_,item,folder=system
    rows=[{'frame_index':i,'timestamp_seconds':i/10,'detections':[{'label':'waterlogging','confidence':.9,'bbox_xyxy':[5,5,40,40]}]} for i in range(6)]
    (folder/'detections.jsonl').write_text(''.join(json.dumps(row)+'\n' for row in rows))
    videos=client.get('/api/v1/government/analysis-results',headers=headers).json()['videos']
    first=videos[0]
    payload={**publication(item),'segment_id':first['detection_segments'][0]['id']}
    response=client.post(f'/api/v1/government/analysis-results/{first["id"]}/incidents',headers=headers,json=payload)
    assert response.status_code==200,response.text
    first_id=response.json()['incident']['id']
    other=folder.parent/'second_waterlogging';other.mkdir()
    for filename in ('summary.json','detections.jsonl','annotated.mp4'):
        shutil.copyfile(folder/filename,other/filename)
    videos=client.get('/api/v1/government/analysis-results',headers=headers).json()['videos']
    second=next(video for video in videos if video['id']!=first['id'])
    path=f'/api/v1/government/analysis-results/{second["id"]}/incidents'
    different_location={**payload,'latitude':13.025,'location_name':'Second assigned location'}
    assert client.post(path,headers=headers,json=different_location).status_code==409
    writer=cv2.VideoWriter(str(other/'annotated.mp4'),cv2.VideoWriter_fourcc(*'mp4v'),10,(64,64))
    for _ in range(6): writer.write(np.full((64,64,3),(130,70,20),dtype=np.uint8))
    writer.release()
    response=client.post(path,headers=headers,json=different_location)
    assert response.status_code==200,response.text
    second_id=response.json()['incident']['id']
    evidence=[client.get(f'/api/v1/government/analysis-results/incidents/{identity}',headers=headers).json() for identity in (first_id,second_id)]
    assert evidence[0]['video_url']!=evidence[1]['video_url']
    assert evidence[0]['frames'][0]['image_url']!=evidence[1]['frames'][0]['image_url']
    records=client.get('/api/v1/user/records').json()
    assert records['total']==records['mapped']==records['with_evidence']==2


def test_changed_detection_never_falls_back_to_unrelated_video_segment(system):
    client,headers,_,item,folder=system
    response=client.post(f'/api/v1/government/analysis-results/{item["id"]}/incidents',headers=headers,json=publication(item))
    event_id=response.json()['incident']['id']
    (folder/'detections.jsonl').write_text(json.dumps({'frame_index':0,'timestamp_seconds':0,'detections':[]})+'\n')
    response=client.get(f'/api/v1/government/analysis-results/incidents/{event_id}',headers=headers)
    assert response.status_code==409
