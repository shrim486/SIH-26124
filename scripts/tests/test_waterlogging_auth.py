from datetime import datetime, timezone
from pathlib import Path
import sys
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from edge_ai.waterlogging.api_client import APIClient


def test_recorded_pipeline_authenticates_and_preserves_simulated_gps(monkeypatch):
    monkeypatch.setenv('GOVERNMENT_USERNAME', 'test-operator')
    monkeypatch.setenv('GOVERNMENT_PASSWORD', 'test-password')
    client = APIClient()
    login = Mock(status_code=200)
    login.json.return_value = {'access_token': 'test-token'}
    expired, success = Mock(status_code=401), Mock(status_code=200)
    client.session = Mock()
    client.session.post.side_effect = [login, expired, login, success]
    alert = dict(event_type='waterlogging', confidence=.8, latitude=13, longitude=77.6,
                 timestamp=datetime.now(timezone.utc).isoformat(), severity='medium', report_count=2, status='open')
    assert client.send_alert(alert)
    calls = client.session.post.call_args_list
    assert calls[0].args[0].endswith('/government/login')
    assert calls[-1].kwargs['headers']['Authorization'] == 'Bearer test-token'
    payload = calls[-1].kwargs['json']
    assert payload['metadata']['is_demo'] is True
    assert 'bus_id' not in payload and 'camera_id' not in payload
