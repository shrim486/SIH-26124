from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from app.db.database import Base


class FleetPosition(Base):
    __tablename__ = 'fleet_positions'
    bus_id = Column(Integer, ForeignKey('buses.id'), primary_key=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    recorded_at = Column(DateTime, nullable=False)
    received_at = Column(DateTime, nullable=False)
    source = Column(String, nullable=False)
