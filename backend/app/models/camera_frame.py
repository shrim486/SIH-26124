from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, LargeBinary
from app.db.database import Base


class CameraFrame(Base):
    """Only the most recent preview is retained for each registered camera."""
    __tablename__ = 'camera_frames'
    camera_id = Column(Integer, ForeignKey('cameras.id'), primary_key=True)
    captured_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)
    content = Column(LargeBinary, nullable=False)
    width = Column(Integer, nullable=False)
    height = Column(Integer, nullable=False)
    processing = Column(String, nullable=False, default='raw')
