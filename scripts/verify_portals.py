"""Read-only live API/media checks. Does not claim browser interaction coverage."""
import json
import subprocess
from collections import Counter
from pathlib import Path

import cv2
import numpy as np
import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000/api/v1'


def main():
    portal_imports = json.loads(subprocess.check_output(
        ['node', str(ROOT / 'scripts/check_portal_imports.mjs'), '--json'], text=True,
    ))
    settings = dotenv_values(ROOT / 'backend/.env')
    session = requests.Session()
    response = session.post(BASE + '/government/login', json={
        'username': settings['GOVERNMENT_USERNAME'], 'password': settings['GOVERNMENT_PASSWORD'],
    }, timeout=20)
    response.raise_for_status()
    session.headers['Authorization'] = 'Bearer ' + response.json()['access_token']

    def get(path, private=True):
        response = (session if private else requests).get(BASE + path, timeout=60)
        response.raise_for_status()
        return response.json()

    checks = []
    for path in ['dashboard', 'statistics', 'road-issues', 'violations', 'accidents', 'fleet', 'analytics', 'map-events', 'alerts', 'auth-check']:
        get('/government/' + path)
        assert requests.get(BASE + '/government/' + path, timeout=15).status_code == 401
        checks.append('government/' + path)
    for path in ['dashboard', 'map-events', 'alerts', 'reports']:
        get('/user/' + path, False)
        checks.append('user/' + path)
    catalog = get('/government/analysis-results')
    assert len(catalog['models']) == 12 and 'samples' not in catalog
    public = {item['id']: item for item in get('/user/map-events', False)}
    incidents = get('/government/analysis-results/incidents')
    frame_count = 0
    for incident in incidents:
        identity = incident['id']
        assert identity in public
        assert public[identity]['latitude'] == incident['latitude']
        assert public[identity]['event_type'] == incident['event_type']
        assert json.loads(public[identity]['event_metadata'])['is_demo'] == incident['demo']
        evidence = get(f'/government/analysis-results/incidents/{identity}')
        assert evidence['incident']['id'] == identity and evidence['frames']
        response = session.get(BASE + evidence['video_url'], headers={'Range':'bytes=0-1023'}, timeout=60)
        assert response.status_code == 206 and len(response.content) == 1024
        assert requests.get(BASE + evidence['video_url'], timeout=15).status_code == 401
        for frame in evidence['frames']:
            response = session.get(BASE + frame['image_url'], timeout=60)
            response.raise_for_status()
            assert cv2.imdecode(np.frombuffer(response.content, dtype=np.uint8), cv2.IMREAD_COLOR) is not None
            frame_count += 1
    decoded = {}
    for summary_path in (ROOT / 'edge_ai/outputs').glob('demo_*/summary.json'):
        summary = json.loads(summary_path.read_text())
        cap = cv2.VideoCapture(str(summary_path.parent / 'annotated.mp4'))
        codec = int(cap.get(cv2.CAP_PROP_FOURCC))
        assert ''.join(chr((codec >> (8 * i)) & 255) for i in range(4)) in {'h264','avc1'}
        count = 0
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            count += 1
        cap.release()
        assert count == summary['frames_processed'] == summary['input']['frames']
        decoded[summary_path.parent.name] = count
    for port, title, routes in [
        (5173, 'user-portal', ['/', '/map', '/report', '/reports', '/alerts', '/government-login']),
        (5174, 'government-portal', ['/', '/detections', '/ai-results', '/road-issues', '/violations', '/accidents', '/alerts', '/fleet', '/analytics']),
    ]:
        for route in routes:
            response = requests.get(f'http://127.0.0.1:{port}{route}', timeout=15)
            response.raise_for_status()
            assert f'<title>{title}</title>' in response.text
    result = {'portal_imports': portal_imports, 'api_routes_verified': checks, 'linked_incidents': len(incidents),
              'types': dict(Counter(item['event_type'] for item in incidents)),
              'evidence_frames_decoded': frame_count, 'annotated_videos_decoded': decoded,
              'models_without_candidates': [model['id'] for model in catalog['models'] if not model['positive_segments']],
              'browser_interaction_verified': False}
    (ROOT / '.runtime').mkdir(exist_ok=True)
    (ROOT / '.runtime/portal-verification.json').write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
