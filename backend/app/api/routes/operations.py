from datetime import datetime, timezone, timedelta
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field, ConfigDict, field_validator
from sqlalchemy.exc import IntegrityError
from app.core.government_auth import require_government_authority
from app.db.database import get_db
from app.models.bus import Bus
from app.models.camera import Camera
from app.models.fleet_position import FleetPosition
from app.models.fleet_history import FleetPositionHistory, CameraHeartbeat
from app.services.issue_service import list_issues, update_issue, issue_history

router = APIRouter(prefix='/government', tags=['Government operations'],
                   dependencies=[Depends(require_government_authority)])


@router.get('/records')
def recorded_alerts(archive: bool = False, db=Depends(get_db)):
    from app.services.alert_service import records_payload
    return records_payload(db, private=True, archive=archive)


@router.get('/issues')
def issues(category: Literal['road', 'violations', 'accidents', 'traffic'] | None = None,
           status: Literal['all', 'open', 'in_progress', 'resolved', 'closed'] | None = None,
           bus_id: int | None = None, db=Depends(get_db)):
    return list_issues(db, category, status, bus_id)


class IssueUpdate(BaseModel):
    status: Literal['open', 'in_progress', 'resolved', 'closed']
    note: str = Field(default='', max_length=1000)


@router.patch('/issues/{event_id}/status')
def change_issue(event_id: int, data: IssueUpdate, db=Depends(get_db), authority=Depends(require_government_authority)):
    return update_issue(db, event_id, data.status, authority['username'], data.note.strip())


@router.get('/issues/{event_id}/history')
def history(event_id: int, db=Depends(get_db)):
    return issue_history(db, event_id)


class BusInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    bus_number: str = Field(min_length=1, max_length=40)
    route_number: str = Field(default='', max_length=40)
    is_active: bool = True


def save_bus(db, bus, data):
    values = data.model_dump()
    values['bus_number'] = values['bus_number'].upper()
    for key, value in values.items():
        setattr(bus, key, value)
    db.add(bus)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Bus number already registered')
    return {'id': bus.id, **values}


@router.post('/fleet/buses', status_code=201)
def add_bus(data: BusInput, db=Depends(get_db)):
    return save_bus(db, Bus(), data)


@router.put('/fleet/buses/{bus_id}')
def edit_bus(bus_id: int, data: BusInput, db=Depends(get_db)):
    bus = db.get(Bus, bus_id)
    if not bus:
        raise HTTPException(404, 'Bus not found')
    return save_bus(db, bus, data)


class CameraInput(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    bus_id: int = Field(gt=0)
    camera_code: str = Field(min_length=1, max_length=60)
    camera_type: Literal['front', 'rear', 'cabin'] = 'front'


@router.post('/fleet/cameras', status_code=201)
def add_camera(data: CameraInput, db=Depends(get_db)):
    if not db.get(Bus, data.bus_id):
        raise HTTPException(404, 'Bus not found')
    if db.query(Camera).filter_by(camera_code=data.camera_code).first():
        raise HTTPException(409, 'Camera code already registered')
    camera = Camera(**data.model_dump(), status='active')
    db.add(camera)
    db.commit()
    return {'id': camera.id, **data.model_dump(), 'status': camera.status}


class CameraStatus(BaseModel):
    status: Literal['active', 'maintenance', 'offline']


@router.patch('/fleet/cameras/{camera_id}')
def camera_status(camera_id: int, data: CameraStatus, db=Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, 'Camera not found')
    camera.status = data.status
    db.commit()
    return {'id': camera.id, 'status': camera.status}


@router.put('/fleet/cameras/{camera_id}')
def edit_camera(camera_id: int, data: CameraInput, db=Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, 'Camera not found')
    if camera.bus_id != data.bus_id:
        raise HTTPException(422, 'Camera bus assignment is fixed to preserve its detection history. Register a new camera for another bus.')
    if db.query(Camera).filter(Camera.camera_code == data.camera_code, Camera.id != camera_id).first():
        raise HTTPException(409, 'Camera code already registered')
    camera.camera_code, camera.camera_type = data.camera_code, data.camera_type
    db.commit()
    return {'id': camera.id, **data.model_dump(), 'status': camera.status}


class PositionInput(BaseModel):
    latitude: float = Field(ge=-90, le=90, allow_inf_nan=False)
    longitude: float = Field(ge=-180, le=180, allow_inf_nan=False)
    recorded_at: datetime
    source: Literal['device', 'manual'] = 'manual'

    @field_validator('recorded_at')
    @classmethod
    def recorded_time(cls, value):
        if value.tzinfo is None:
            raise ValueError('Recording time must include timezone')
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
        if value > datetime.utcnow() + timedelta(seconds=60):
            raise ValueError('Recording time cannot be in the future')
        return value


@router.post('/fleet/buses/{bus_id}/position')
def report_position(bus_id: int, data: PositionInput, db=Depends(get_db)):
    if not db.get(Bus, bus_id):
        raise HTTPException(404, 'Bus not found')
    position = db.get(FleetPosition, bus_id)
    if position and data.recorded_at <= position.recorded_at:
        raise HTTPException(409, 'Position must be newer than the last recorded position')
    if position is None:
        position = FleetPosition(bus_id=bus_id)
        db.add(position)
    for key, value in data.model_dump().items():
        setattr(position, key, value)
    position.received_at = datetime.utcnow()
    db.add(FleetPositionHistory(bus_id=bus_id, **data.model_dump(), received_at=position.received_at))
    db.commit()
    return {'bus_id': bus_id, 'saved': True, 'source': position.source}


@router.get('/fleet/buses/{bus_id}/history')
def position_history(bus_id: int, hours: int = Query(24, ge=1, le=168), limit: int = Query(1000, ge=1, le=3000), db=Depends(get_db)):
    from app.services.alert_service import iso
    if not db.get(Bus, bus_id):
        raise HTTPException(404, 'Bus not found')
    cutoff = datetime.utcnow() - timedelta(hours=hours)
    rows = db.query(FleetPositionHistory).filter(FleetPositionHistory.bus_id == bus_id,
        FleetPositionHistory.recorded_at >= cutoff).order_by(FleetPositionHistory.recorded_at.desc(), FleetPositionHistory.id.desc()).limit(limit+1).all()
    truncated = len(rows)>limit
    rows = list(reversed(rows[:limit]))
    # Preserve visibility of positions received before history collection was introduced.
    if not rows:
        last = db.get(FleetPosition, bus_id)
        if last and last.recorded_at >= cutoff:
            rows = [last]
    return dict(bus_id=bus_id, hours=hours, truncated=truncated, points=[dict(latitude=row.latitude,
        longitude=row.longitude, recorded_at=iso(row.recorded_at), received_at=iso(row.received_at), source=row.source) for row in rows])


class HeartbeatInput(BaseModel):
    recorded_at: datetime
    last_frame_at: datetime | None = None
    state: Literal['ok', 'error'] = 'ok'
    message: str = Field(default='', max_length=250)

    @field_validator('recorded_at', 'last_frame_at')
    @classmethod
    def valid_time(cls, value):
        return PositionInput.recorded_time(value) if value is not None else None


@router.post('/fleet/cameras/{camera_id}/heartbeat')
def camera_heartbeat(camera_id: int, data: HeartbeatInput, db=Depends(get_db)):
    if not db.get(Camera, camera_id):
        raise HTTPException(404, 'Camera not found')
    if data.last_frame_at and data.last_frame_at > data.recorded_at:
        raise HTTPException(422, 'Frame time cannot be later than the heartbeat time')
    heartbeat = db.get(CameraHeartbeat, camera_id)
    if heartbeat and data.recorded_at <= heartbeat.recorded_at:
        raise HTTPException(409, 'Heartbeat must be newer than the last report')
    if heartbeat is None:
        heartbeat = CameraHeartbeat(camera_id=camera_id)
        db.add(heartbeat)
    for key, value in data.model_dump().items():
        setattr(heartbeat, key, value)
    heartbeat.received_at = datetime.utcnow()
    db.commit()
    return {'camera_id': camera_id, 'saved': True}
