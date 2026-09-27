import base64
from datetime import datetime, timedelta, timezone
from io import BytesIO
from PIL import Image
from test_accident_evidence import system
from test_fleet_and_records import register
from app.models.camera_frame import CameraFrame

ROOT = '/api/v1/government/fleet'


def camera(system):
    client, headers = system[:2]
    bus = register(client, headers)
    row = client.post(ROOT+'/cameras', headers=headers, json={'bus_id':bus,'camera_code':'LIVE-FRONT'}).json()
    return f"{ROOT}/cameras/{row['id']}/frame"


def payload(seconds=0, size=(160,90), format='JPEG'):
    image = BytesIO()
    Image.new('RGB', size, (40,120,80)).save(image, format=format)
    return {'captured_at':(datetime.now(timezone.utc)+timedelta(seconds=seconds)).isoformat(),
            'jpeg_base64':base64.b64encode(image.getvalue()).decode(), 'processing':'raw'}


def test_camera_preview_auth_freshness_replacement_and_health(system):
    client, headers, sessions = system[:3]
    path = camera(system)
    assert client.get(path).status_code == 401
    assert client.get(path,headers=headers).status_code == 404
    first = payload(-20)
    assert client.post(path,json=first).status_code == 401
    assert client.post(path,headers=headers,json=first).status_code == 200
    fleet = client.get(ROOT,headers=headers).json()
    assert fleet['cameras'][0]['preview_available'] and not fleet['cameras'][0]['preview_live']
    assert fleet['online_buses'] == 0  # Images must not invent GPS.
    second = payload()
    second['processing'] = 'pothole'
    assert client.post(path,headers=headers,json=second).status_code == 200
    assert client.post(path,headers=headers,json=first).status_code == 409
    assert client.post(path,headers=headers,json=second).status_code == 409
    response = client.get(path,headers=headers)
    assert response.status_code == 200 and response.headers['cache-control'] == 'private, no-store'
    assert response.headers['x-frame-processing'] == 'pothole'
    assert response.headers['x-captured-at'] == second['captured_at']
    assert Image.open(BytesIO(response.content)).size == (160,90)
    with sessions() as db:
        assert db.query(CameraFrame).count() == 1
    fleet = client.get(ROOT,headers=headers).json()
    assert fleet['live_previews'] == 1 and fleet['cameras_receiving_frames'] == 1
    assert fleet['cameras'][0]['preview_processing'] == 'pothole'
    assert client.get('/api/v1/user/records').json()['total'] == 0


def test_camera_preview_rejects_bad_images_times_unknown_and_inactive_cameras(system):
    client, headers = system[:2]
    path = camera(system)
    bad = [payload(-180), payload(180), payload(size=(1921,10)), payload(format='PNG'),
           {**payload(),'jpeg_base64':'dGV4dA=='}, {**payload(),'jpeg_base64':'!'*20},
           {**payload(),'captured_at':'2026-09-27T12:00:00'}, {**payload(),'jpeg_base64':'a'*700000}]
    for row in bad:
        assert client.post(path,headers=headers,json=row).status_code == 422
    assert client.post(ROOT+'/cameras/999/frame',headers=headers,json=payload()).status_code == 404
    assert client.get(ROOT,headers=headers).json()['live_previews'] == 0
    assert client.post(path,headers=headers,json=payload()).status_code == 200
    assert client.patch(path.removesuffix('/frame'),headers=headers,json={'status':'offline'}).status_code == 200
    assert client.get(ROOT,headers=headers).json()['live_previews'] == 0
    assert client.post(path,headers=headers,json=payload()).status_code == 409
