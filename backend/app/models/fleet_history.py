from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Index
from app.db.database import Base


class FleetPositionHistory(Base):
    __tablename__ = 'fleet_position_history'
    id = Column(Integer, primary_key=True)
    bus_id = Column(Integer, ForeignKey('buses.id'), nullable=False)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=False)
    __table_args__ = (Index('ix_fleet_history_bus_time', 'bus_id', 'recorded_at'),)


class CameraHeartbeat(Base):
    __tablename__ = 'camera_heartbeats'
    camera_id = Column(Integer, ForeignKey('cameras.id'), primary_key=True)
    recorded_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)
    last_frame_at = Column(DateTime, nullable=True)
    state = Column(String, nullable=False)
    message = Column(String(250), nullable=False, default='')
