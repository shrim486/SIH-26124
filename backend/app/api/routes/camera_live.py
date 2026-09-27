"""Authenticated, bounded latest-frame ingestion from a camera edge device."""
import base64
import binascii
from datetime import datetime, timedelta
from io import BytesIO
from typing import Literal
from fastapi import APIRouter, Depends, HTTPException, Response
from PIL import Image, UnidentifiedImageError
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import update
from sqlalchemy.exc import IntegrityError
from app.api.routes.operations import PositionInput
from app.core.government_auth import require_government_authority
from app.db.database import get_db
from app.models.camera import Camera
from app.models.camera_frame import CameraFrame
from app.models.fleet_history import CameraHeartbeat
from app.services.alert_service import iso

router = APIRouter(prefix='/government/fleet/cameras', tags=['Live cameras'],
                   dependencies=[Depends(require_government_authority)])
MAX_BYTES = 512 * 1024


class FrameInput(BaseModel):
    captured_at: datetime
    jpeg_base64: str = Field(min_length=4, max_length=4*((MAX_BYTES+2)//3))
    processing: Literal['raw', 'pothole'] = 'raw'

    @field_validator('captured_at')
    @classmethod
    def recording_time(cls, value):
        value = PositionInput.recorded_time(value)
        if value < datetime.utcnow() - timedelta(seconds=120):
            raise ValueError('Live preview must be captured within the last two minutes')
        return value


def jpeg_content(value):
    try:
        content = base64.b64decode(value, validate=True)
        if len(content) > MAX_BYTES:
            raise HTTPException(413, 'Preview exceeds 512 KiB')
        with Image.open(BytesIO(content)) as image:
            if image.format != 'JPEG' or image.width > 1920 or image.height > 1080:
                raise HTTPException(422, 'Send a JPEG preview up to 1920 by 1080 pixels')
            image.load()
            # Re-encode to remove embedded metadata and trailing non-image content.
            clean = BytesIO()
            image.convert('RGB').save(clean, format='JPEG', quality=80)
            if clean.tell() > MAX_BYTES:
                raise HTTPException(413, 'Preview exceeds 512 KiB after decoding')
            return clean.getvalue(), image.width, image.height
    except (binascii.Error, ValueError, OSError, UnidentifiedImageError, Image.DecompressionBombError) as error:
        raise HTTPException(422, 'Invalid JPEG preview') from error


@router.post('/{camera_id}/frame')
def receive_frame(camera_id: int, data: FrameInput, db=Depends(get_db)):
    camera = db.get(Camera, camera_id)
    if not camera:
        raise HTTPException(404, 'Camera not found')
    if camera.status != 'active':
        raise HTTPException(409, 'Activate this camera before sending frames')
    content, width, height = jpeg_content(data.jpeg_base64)
    now = datetime.utcnow()
    values = dict(captured_at=data.captured_at, received_at=now, content=content,
                  width=width, height=height, processing=data.processing)
    changed = db.execute(update(CameraFrame).where(CameraFrame.camera_id == camera_id,
        CameraFrame.captured_at < data.captured_at).values(**values)).rowcount
    if not changed:
        if db.get(CameraFrame, camera_id):
            db.rollback()
            raise HTTPException(409, 'Frame must be newer than the last preview')
        db.add(CameraFrame(camera_id=camera_id, **values))
    heartbeat = db.get(CameraHeartbeat, camera_id)
    if heartbeat is None:
        heartbeat = CameraHeartbeat(camera_id=camera_id)
        db.add(heartbeat)
    if heartbeat.recorded_at is None or heartbeat.recorded_at <= data.captured_at:
        heartbeat.recorded_at = data.captured_at
        heartbeat.received_at = now
        heartbeat.last_frame_at = data.captured_at
        heartbeat.state, heartbeat.message = 'ok', ''
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(409, 'Another frame arrived; send the next captured frame')
    return dict(camera_id=camera_id, captured_at=iso(data.captured_at), saved=True)


@router.get('/{camera_id}/frame')
def latest_frame(camera_id: int, db=Depends(get_db)):
    if not db.get(Camera, camera_id):
        raise HTTPException(404, 'Camera not found')
    frame = db.get(CameraFrame, camera_id)
    if not frame:
        raise HTTPException(404, 'Waiting for the first camera frame')
    return Response(frame.content, media_type='image/jpeg', headers={
        'Cache-Control': 'no-store', 'X-Content-Type-Options': 'nosniff',
        'X-Captured-At': iso(frame.captured_at), 'X-Received-At': iso(frame.received_at),
        'X-Frame-Processing': frame.processing,
    })
