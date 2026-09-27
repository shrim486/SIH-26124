"""Send real camera previews and optional device GPS to fleet monitoring."""
import argparse
import base64
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import threading
import time
from urllib.parse import urlsplit

import cv2
import httpx
from dotenv import load_dotenv


def camera_source(value):
    if value.isdigit():
        return int(value)
    if urlsplit(value).scheme.lower() in {'rtsp', 'rtsps', 'http', 'https'}:
        return value
    raise ValueError('Set URBANIQ_CAMERA_SOURCE to an RTSP/HTTP camera URL or a USB camera index. Recorded files are not live sources.')


def gps_position(path, now=None):
    """Read a real GPS-device fix; reject missing, old, naive and invalid fixes."""
    if not path:
        return None
    try:
        with Path(path).open(encoding='utf-8') as handle:
            row = json.loads(handle.read(4096))
        latitude, longitude = float(row['latitude']), float(row['longitude'])
        recorded = datetime.fromisoformat(row['recorded_at'].replace('Z', '+00:00'))
        now = now or datetime.now(timezone.utc)
        if recorded.tzinfo is None or not -5 <= (now-recorded).total_seconds() <= 30:
            return None
        if not (math.isfinite(latitude) and math.isfinite(longitude) and abs(latitude)<=90 and abs(longitude)<=180):
            return None
        return dict(latitude=latitude, longitude=longitude, recorded_at=recorded.isoformat(), source='device')
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


def preview_jpeg(frame):
    height, width = frame.shape[:2]
    scale = min(1, 1280/width, 720/height)
    if scale < 1:
        frame = cv2.resize(frame, (max(1,round(width*scale)), max(1,round(height*scale))))
    for quality in (75, 60, 45):
        ok, data = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, quality])
        if ok and len(data) <= 512*1024:
            return base64.b64encode(data).decode('ascii')
    raise ValueError('Could not encode a bounded camera preview')


class Capture:
    """Continuously drain capture buffers while inference/upload runs separately."""
    def __init__(self, source):
        self.source, self.latest = source, None
        self.lock, self.stop = threading.Lock(), threading.Event()
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        sequence = 0
        while not self.stop.is_set():
            cap = None
            try:
                if isinstance(self.source, int):
                    cap = cv2.VideoCapture(self.source)
                else:
                    cap = cv2.VideoCapture(self.source, cv2.CAP_FFMPEG, [
                        cv2.CAP_PROP_OPEN_TIMEOUT_MSEC, 10000, cv2.CAP_PROP_READ_TIMEOUT_MSEC, 5000])
                while not self.stop.is_set() and cap.isOpened():
                    ok, frame = cap.read()
                    if not ok:
                        break
                    sequence += 1
                    with self.lock:
                        self.latest = (sequence, datetime.now(timezone.utc), frame)
            except cv2.error:
                # Retry without leaking a credential-bearing source in a traceback.
                pass
            finally:
                if cap is not None:
                    cap.release()
            self.stop.wait(3)

    def frame(self):
        with self.lock:
            return self.latest


class FleetClient:
    def __init__(self, base, username, password):
        self.username, self.password = username, password
        self.client = httpx.Client(base_url=base.rstrip('/')+'/', timeout=15)

    def login(self):
        response = self.client.post('government/login', json={'username':self.username, 'password':self.password})
        if response.status_code != 200:
            raise RuntimeError('Camera connector sign-in failed. Check local credentials and API access.')
        self.client.headers['Authorization'] = 'Bearer '+response.json()['access_token']

    def send(self, method, path, **kwargs):
        response = self.client.request(method, path, **kwargs)
        if response.status_code == 401:
            self.login()
            response = self.client.request(method, path, **kwargs)
        if not response.is_success:
            raise RuntimeError(f'Camera API returned HTTP {response.status_code}. Check registration, camera status and device clock.')
        return response.json()


def run(args):
    load_dotenv(args.env_file, override=False)
    source = camera_source(os.environ.get('URBANIQ_CAMERA_SOURCE', ''))
    username, password = os.environ.get('URBANIQ_USERNAME'), os.environ.get('URBANIQ_PASSWORD')
    if not username or not password:
        raise ValueError('Configure URBANIQ_USERNAME and URBANIQ_PASSWORD locally before starting the connector.')
    detector = None
    if args.pothole:
        from edge_ai.config.config import BASE_DIR
        from edge_ai.detectors.road_hazards.pothole_detector import RoadDetector
        detector = RoadDetector(BASE_DIR/'models/road_hazards/pothole/best.onnx', confidence=args.conf)
    # Do not write camera URLs/passwords to application logs.
    cv2.setLogLevel(0)
    client = FleetClient(os.environ.get('URBANIQ_API_BASE','http://127.0.0.1:8000/api/v1'),username,password)
    capture = Capture(source)
    try:
        client.login()
        fleet = client.send('GET','government/fleet')
        camera = next((row for row in fleet['cameras'] if row['id']==args.camera_id),None)
        if not camera:
            raise ValueError('Register this camera in Fleet monitoring before connecting it.')
        if camera['status'] != 'active':
            raise ValueError('Set this camera to active in Fleet monitoring before connecting it.')
        capture.thread.start()
        print(f"Camera {args.camera_id} connector started. Waiting for captured frames.",flush=True)
        last_sequence, last_health, last_gps = 0, 0, None
        connected_at = time.monotonic()
        while True:
            started = time.monotonic()
            item = capture.frame()
            now = datetime.now(timezone.utc)
            try:
                if item and item[0] != last_sequence and (now-item[1]).total_seconds() <= 10:
                    sequence, recorded, frame = item
                    if detector:
                        from edge_ai.processing.annotations import draw_frame
                        boxes = [dict(row,label='pothole') for row in detector.predict(frame)]
                        frame = draw_frame(frame,boxes,time.monotonic()-connected_at)
                    client.send('POST', f'government/fleet/cameras/{args.camera_id}/frame', json={
                        'captured_at':recorded.isoformat(), 'jpeg_base64':preview_jpeg(frame),
                        'processing':'pothole' if detector else 'raw'})
                    if last_sequence == 0:
                        print('First frame delivered. Open Fleet monitoring to view this camera.',flush=True)
                    last_sequence = sequence
                elif (not item or (now-item[1]).total_seconds()>10) and started-last_health >= 15:
                    client.send('POST', f'government/fleet/cameras/{args.camera_id}/heartbeat', json={
                        'recorded_at':now.isoformat(), 'state':'error', 'message':'No recent frame from camera; reconnecting'})
                    last_health = started
                position = gps_position(os.environ.get('URBANIQ_GPS_FILE'))
                if position and position['recorded_at'] != last_gps:
                    client.send('POST',f"government/fleet/buses/{camera['bus_id']}/position",json=position)
                    last_gps = position['recorded_at']
            except (httpx.HTTPError, RuntimeError) as error:
                # URL-bearing network errors are intentionally not printed.
                print(str(error) if isinstance(error, RuntimeError) else 'Camera API unreachable; retrying.',flush=True)
            time.sleep(max(.05,args.interval-(time.monotonic()-started)))
    finally:
        capture.stop.set()
        if capture.thread.is_alive():
            capture.thread.join(timeout=12)
        client.client.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--camera-id',type=int,required=True)
    parser.add_argument('--env-file',default='edge_ai/.env.camera')
    parser.add_argument('--interval',type=float,default=2,help='Seconds between preview uploads, 1–30')
    parser.add_argument('--pothole',action='store_true',help='Run the existing pothole model and draw boxes on previews')
    parser.add_argument('--conf',type=float,default=.4)
    args = parser.parse_args()
    if args.camera_id < 1 or not 1<=args.interval<=30 or not 0<args.conf<1:
        parser.error('Use a positive camera ID, interval 1–30 and confidence between 0 and 1.')
    try:
        run(args)
    except KeyboardInterrupt:
        print('Camera connector stopped.')
    except (ValueError, RuntimeError) as error:
        parser.exit(1,str(error)+'\n')
    except httpx.HTTPError:
        parser.exit(1,'Camera API unreachable. Check the configured API address and network.\n')


if __name__ == '__main__':
    main()
