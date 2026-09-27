from datetime import datetime
from collections import defaultdict
from app.models.bus import Bus
from app.models.camera import Camera
from app.models.fleet_position import FleetPosition
from app.models.fleet_history import CameraHeartbeat
from app.models.camera_frame import CameraFrame
from app.services.alert_service import iso
from app.services.issue_service import list_issues, FINISHED


def recent(value, now):
    return value is not None and -60 <= (now-value).total_seconds() <= 120


def get_fleet(db):
    now = datetime.utcnow()
    positions = {row.bus_id: row for row in db.query(FleetPosition).all()}
    heartbeats = {row.camera_id: row for row in db.query(CameraHeartbeat).all()}
    previews = {row.camera_id: row for row in db.query(CameraFrame.camera_id, CameraFrame.captured_at, CameraFrame.processing).all()}
    issues, installed = defaultdict(list), defaultdict(list)
    for issue in list_issues(db):
        for bus_id in issue['source_bus_ids']:
            issues[bus_id].append(issue)
    cameras = []
    for camera in db.query(Camera).order_by(Camera.id).all():
        beat = heartbeats.get(camera.id)
        preview = previews.get(camera.id)
        health = 'no_telemetry' if beat is None else 'stale' if not recent(beat.recorded_at, now) else 'error' if beat.state == 'error' else 'frames_recent' if recent(beat.last_frame_at, now) else 'no_recent_frames'
        row = dict(id=camera.id,bus_id=camera.bus_id,camera_code=camera.camera_code,camera_type=camera.camera_type,status=camera.status,
            health=health,last_seen=iso(beat.recorded_at) if beat else None,last_frame_at=iso(beat.last_frame_at) if beat else None,
            health_message=beat.message if beat else '',receiving_frames=health=='frames_recent',
            preview_available=preview is not None, preview_captured_at=iso(preview.captured_at) if preview else None,
            preview_live=bool(camera.status=='active' and preview and -60 <= (now-preview.captured_at).total_seconds() <= 15),
            preview_processing=preview.processing if preview else None)
        cameras.append(row); installed[camera.bus_id].append(row)
    buses = []
    for bus in db.query(Bus).order_by(Bus.id).all():
        position = positions.get(bus.id)
        online = bool(bus.is_active and position and position.source == 'device' and recent(position.recorded_at,now))
        linked, devices = issues[bus.id], installed[bus.id]
        status = 'inactive' if not bus.is_active else 'online' if online else 'no_telemetry' if position is None else 'manual_location' if position.source == 'manual' else 'stale'
        attention = []
        if bus.is_active:
            if not online: attention.append('GPS update needed')
            if not devices: attention.append('No cameras registered')
            elif any(c['status'] != 'active' or not c['receiving_frames'] for c in devices): attention.append('Camera check needed')
        buses.append(dict(id=bus.id,bus_number=bus.bus_number,route_number=bus.route_number,is_active=bus.is_active,
            online=online,connection_status=status,latitude=position.latitude if position else None,longitude=position.longitude if position else None,
            last_seen=iso(position.recorded_at) if position else None,received_at=iso(position.received_at) if position else None,
            location_source=position.source if position else None,position_age_seconds=max(0,int((now-position.recorded_at).total_seconds())) if position else None,
            camera_count=len(devices),cameras_receiving_frames=sum(c['receiving_frames'] for c in devices),attention=attention,
            issue_count=len(linked),open_issues=sum(item['status'] not in FINISHED for item in linked)))
    return dict(total_buses=len(buses),total_cameras=len(cameras),online_buses=sum(bus['online'] for bus in buses),
        active_buses=sum(bus['is_active'] for bus in buses),attention_buses=sum(bool(bus['attention']) for bus in buses),
        cameras_receiving_frames=sum(c['receiving_frames'] for c in cameras),live_previews=sum(c['preview_live'] for c in cameras),buses=buses,cameras=cameras,updated_at=iso(now))
