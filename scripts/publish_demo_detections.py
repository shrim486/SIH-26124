"""Publish actual saved candidates at explicitly simulated Bengaluru locations.

Safe to rerun: the backend keys each record by run and segment. No model
predictions, real locations, emergency alerts, or enforcement records are invented.
"""
import json
from datetime import datetime, timezone
from pathlib import Path

import requests
from dotenv import dotenv_values

ROOT = Path(__file__).resolve().parents[1]
BASE = 'http://127.0.0.1:8000/api/v1'


def select_candidates(videos):
    candidates = []
    for video in videos:
        if not (video['name'].startswith('demo ') or video['name'] == 'extended suite reviewed'):
            continue
        for segment in video['detection_segments']:
            kind = segment['event_type']
            if kind in {'helmet', 'number_plate'} and video['name'] != 'demo slow riders':
                continue
            if kind == 'waterlogging' and video['name'] != 'demo waterlogging':
                continue
            if video['name'] == 'extended suite reviewed' and kind == 'traffic_sign':
                continue
            candidates.append((video, segment))
    # One waterlogging marker/video; one strong plate segment; enough helmet
    # segments to show both actual classes without publishing every brief gap.
    curated = [row for row in candidates if row[1]['event_type'] not in {'waterlogging', 'number_plate', 'helmet'}]
    for kind in ('waterlogging', 'number_plate', 'helmet'):
        rows = sorted((row for row in candidates if row[1]['event_type'] == kind),
                      key=lambda row: (len(row[1].get('detected_labels', [])), row[1]['detected_frames']), reverse=True)
        covered = set()
        for row in rows:
            labels = set(row[1].get('detected_labels', []))
            if not covered or (kind == 'helmet' and labels - covered):
                curated.append(row)
                covered.update(labels or {kind})
            if kind != 'helmet' or {'with_helmet', 'without_helmet'} <= covered:
                break
    return sorted(curated, key=lambda row: (row[0]['id'], row[1]['id']))


def main():
    settings = dotenv_values(ROOT / 'backend/.env')
    session = requests.Session()
    response = session.post(BASE + '/government/login', json={
        'username': settings['GOVERNMENT_USERNAME'], 'password': settings['GOVERNMENT_PASSWORD'],
    }, timeout=20)
    response.raise_for_status()
    session.headers['Authorization'] = 'Bearer ' + response.json()['access_token']
    response = session.get(BASE + '/government/analysis-results', timeout=60)
    response.raise_for_status()
    catalog = response.json()
    candidates = select_candidates(catalog['videos'])
    records = []
    for index, (video, segment) in enumerate(candidates):
        existing = next((link for link in video['published_incidents'] if link['segment_id'] == segment['id']), None)
        if existing:
            event_id = existing['id']
        else:
            fraction = index / max(1, len(candidates) - 1)
            latitude = round(13.096 - .162 * fraction, 6)
            longitude = round(77.596 + .029 * fraction + (.001 if index % 2 else -.001), 6)
            description = f"Model candidate from {video['name']}, at {segment['start_seconds']:.2f}-{segment['end_seconds']:.2f}s. Bengaluru coordinates and time are simulated; this footage was not recorded at this map location."
            if video['name'] == 'demo slow riders':
                description += ' Same rider video for helmet and plate review; green = with helmet, red = without helmet, blue = plate. OCR text requires visual verification.'
            if video['name'] == 'demo triple riders':
                description += ' This is a staged film excerpt used by the sample publisher, not real incident footage.'
            payload = {
                'segment_id': segment['id'], 'latitude': latitude, 'longitude': longitude,
                'occurred_at': datetime.now(timezone.utc).isoformat(),
                'location_name': f'{latitude:.6f}, {longitude:.6f}',
                'description': description, 'demo': True,
            }
            response = session.post(BASE + f'/government/analysis-results/{video["id"]}/incidents', json=payload, timeout=90)
            response.raise_for_status()
            event_id = response.json()['incident']['id']
        records.append({'event_id': event_id, 'event_type': segment['event_type'], 'run': video['name'], 'segment_id': segment['id']})
    target = ROOT / '.runtime/multi-demo-publication.json'
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(records, indent=2), encoding='utf-8')
    print(json.dumps(records, indent=2))


if __name__ == '__main__':
    main()
