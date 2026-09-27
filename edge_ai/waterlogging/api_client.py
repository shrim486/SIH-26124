"""Send recorded-video alerts through government authentication."""
import os
from pathlib import Path

from dotenv import dotenv_values
import requests


class APIClient:
    def __init__(self, backend_url='http://127.0.0.1:8000/api/v1/events/ingest'):
        self.backend_url = backend_url
        self.login_url = backend_url.split('/events', 1)[0] + '/government/login'
        local = dotenv_values(Path(__file__).resolve().parents[2] / 'backend/.env')
        self.username = os.getenv('GOVERNMENT_USERNAME') or local.get('GOVERNMENT_USERNAME')
        self.password = os.getenv('GOVERNMENT_PASSWORD') or local.get('GOVERNMENT_PASSWORD')
        self.token = None
        self.session = requests.Session()

    def login(self):
        if not self.username or not self.password:
            raise ValueError('Configure government credentials in backend/.env or the edge process environment.')
        response = self.session.post(self.login_url, json={'username': self.username, 'password': self.password}, timeout=10)
        response.raise_for_status()
        self.token = response.json()['access_token']

    def send_alert(self, alert):
        payload = {key: alert[key] for key in ('event_type', 'confidence', 'latitude', 'longitude', 'timestamp', 'severity')}
        # Recorded footage and SimulatedGPS are not registered fleet telemetry.
        payload['metadata'] = {'source': 'edge_ai', 'model': 'waterlogging',
                               'report_count': alert['report_count'], 'status': alert['status'],
                               'is_demo': True, 'location_source': 'simulated', 'time_source': 'simulated'}
        try:
            if not self.token:
                self.login()
            response = self.session.post(self.backend_url, json=payload,
                                         headers={'Authorization': 'Bearer ' + self.token}, timeout=10)
            if response.status_code == 401:
                self.login()
                response = self.session.post(self.backend_url, json=payload,
                                             headers={'Authorization': 'Bearer ' + self.token}, timeout=10)
            response.raise_for_status()
            print('Waterlogging alert sent successfully.')
            return True
        except (requests.RequestException, ValueError, KeyError) as error:
            print(f'Waterlogging alert was not sent ({type(error).__name__}). Check government credentials and backend availability.')
            return False
