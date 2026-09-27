import base64
from datetime import datetime, timedelta, timezone
import json
import cv2
import numpy as np
import pytest
from edge_ai.live_camera import camera_source, gps_position, preview_jpeg


def test_camera_sources_exclude_recorded_video():
    assert camera_source('0') == 0
    assert camera_source('rtsp://camera.local/live') == 'rtsp://camera.local/live'
    for value in ('video.mp4', 'file:///recording.mp4', '', 'camera-name'):
        with pytest.raises(ValueError):
            camera_source(value)


def test_gps_requires_recent_finite_timezone_aware_fix(tmp_path):
    now = datetime.now(timezone.utc)
    path = tmp_path/'gps.json'
    row = dict(latitude=13.1, longitude=77.6, recorded_at=now.isoformat())
    path.write_text(json.dumps(row))
    assert gps_position(path,now)['source'] == 'device'
    for changes in ({'latitude':float('nan')},{'longitude':181},
                    {'recorded_at':(now-timedelta(minutes=1)).isoformat()},
                    {'recorded_at':now.replace(tzinfo=None).isoformat()},
                    {'recorded_at':(now+timedelta(minutes=1)).isoformat()}):
        path.write_text(json.dumps({**row,**changes}))
        assert gps_position(path,now) is None
    assert gps_position(None,now) is None


def test_preview_preserves_aspect_ratio_and_bounded_jpeg_size():
    image = np.full((1080,1920,3),80,dtype=np.uint8)
    data = base64.b64decode(preview_jpeg(image))
    assert len(data) <= 512*1024
    decoded = cv2.imdecode(np.frombuffer(data,dtype=np.uint8),cv2.IMREAD_COLOR)
    assert decoded.shape[:2] == (720,1280)
