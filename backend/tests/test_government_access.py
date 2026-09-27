import re
from datetime import datetime, timedelta, timezone
from unittest.mock import patch
import pytest
from jose import jwt
from test_accident_evidence import system, publication
from app.main import app
from app.core.config import settings
from app.core.security import create_access_token
from app.core.login_attempts import LoginAttempts
from app.api.routes import government, video_analysis
from app.services.alert_service import public_metadata


def claims(**changes):
    return {'sub':settings.GOVERNMENT_USERNAME, 'role':'government_authority',
            'exp':datetime.now(timezone.utc)+timedelta(minutes=5), **changes}


def signed(payload, key=None):
    return jwt.encode(payload, key or settings.SECRET_KEY, algorithm=settings.ALGORITHM)


@pytest.mark.parametrize('token_kind', ['anonymous','citizen','wrong_role','expired','forged','missing_exp'])
def test_every_private_api_requires_valid_government_authority(system, token_kind):
    client = system[0]
    no_exp = claims(); no_exp.pop('exp')
    tokens = {'anonymous':None, 'citizen':create_access_token(settings.GOVERNMENT_USERNAME),
              'wrong_role':signed(claims(role='citizen')), 'expired':signed(claims(exp=datetime.now(timezone.utc)-timedelta(minutes=1))),
              'forged':signed(claims(), 'untrusted-test-key'), 'missing_exp':signed(no_exp)}
    token = tokens[token_kind]
    headers = {'Authorization':'Bearer '+token} if token else {}
    checked = 0
    for path, operations in app.openapi()['paths'].items():
        if not path.startswith(('/api/v1/government', '/api/v1/video-analysis', '/api/v1/events')) or path=='/api/v1/government/login':
            continue
        path = re.sub(r'\{[^}]+\}', '1', path)
        for method in set(operations) & {'get','post','put','patch','delete'}:
            result = client.request(method,path,headers=headers,json={} if method!='get' else None)
            assert result.status_code in {401,403}, (token_kind,method,path,result.status_code)
            assert result.headers['cache-control']=='private, no-store'
            checked += 1
    assert checked >= 25


def test_evidence_bytes_and_ranges_only_work_for_government(system):
    client, headers, _, item, _ = system
    published = client.post(f'/api/v1/government/analysis-results/{item["id"]}/incidents',headers=headers,json=publication(item))
    identity = published.json()['incident']['id']
    data = client.get(f'/api/v1/government/analysis-results/incidents/{identity}',headers=headers).json()
    paths = [data['video_url'],data['frames'][0]['image_url']]
    citizen = {'Authorization':'Bearer '+create_access_token('citizen'), 'Range':'bytes=0-31'}
    for path in paths:
        assert client.get('/api/v1'+path).status_code==401
        assert client.get('/api/v1'+path,headers=citizen).status_code==403
        result = client.get('/api/v1'+path,headers={**headers,'Range':'bytes=0-31'})
        assert result.status_code==206 and len(result.content)==32
        assert result.headers['cache-control']=='private, no-store'
    assert client.get('/api/v1/user/records').json()['total']==1


def test_uploaded_video_is_private_and_authorized_upload_still_works(system, tmp_path):
    client, headers = system[:2]
    with patch.object(video_analysis,'JOBS_ROOT',tmp_path), patch.object(video_analysis,'process_video'):
        path='/api/v1/video-analysis'
        assert client.post(path,files={'file':('clip.mp4',b'fixture')}).status_code==401
        assert not (tmp_path/'uploads').exists() and not (tmp_path/'jobs').exists()
        result=client.post(path,headers=headers,files={'file':('clip.mp4',b'fixture')})
        assert result.status_code==202
        identity=result.json()['id']
        video_analysis.jobs[identity]['status']='complete'
        output=tmp_path/identity; output.mkdir(); (output/'annotated.mp4').write_bytes(b'private-video-fixture')
        for resource in (f'{path}/{identity}',f'{path}/{identity}/video'):
            assert client.get(resource).status_code==401
            assert client.get(resource,headers={'Authorization':'Bearer '+create_access_token('citizen')}).status_code==403
            assert client.get(resource,headers=headers).status_code==200
        video_analysis.jobs.pop(identity)


def test_public_metadata_does_not_export_new_private_fields():
    value={'is_demo':True,'location_name':'Mapped point','evidence_available':True,
           'helmet_plate_matches':[{'plate_text':'PRIVATE-PLATE'}], 'image_base64':'private-image',
           'video_url':'private-video', 'frames':[{'image_url':'private-frame'}], 'capture_path':'private-path'}
    assert public_metadata(value)=={'is_demo':True,'location_name':'Mapped point','evidence_available':True}


def test_login_checks_credentials_and_throttles_failed_attempts(system, monkeypatch):
    client=system[0]
    monkeypatch.setattr(government,'login_attempts',LoginAttempts())
    path='/api/v1/government/login'
    login=client.post(path,json={'username':settings.GOVERNMENT_USERNAME,'password':settings.GOVERNMENT_PASSWORD})
    assert login.status_code==200 and login.headers['cache-control']=='private, no-store'
    authority=client.get('/api/v1/government/auth-check',headers={'Authorization':'Bearer '+login.json()['access_token']}).json()
    assert authority['role']=='government_authority' and authority['expires_at']>datetime.now(timezone.utc).timestamp()
    for _ in range(5):
        assert client.post(path,json={'username':'invalid-account','password':'invalid-password'}).status_code==401
    limited=client.post(path,json={'username':'invalid-account','password':'invalid-password'})
    assert limited.status_code==429 and int(limited.headers['retry-after'])>0
