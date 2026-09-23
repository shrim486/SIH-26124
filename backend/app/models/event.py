from datetime import datetime

from sqlalchemy import Column, DateTime, Float, Integer, String, Text

from app.db.database import Base


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True, index=True)

    event_type = Column(String, nullable=False, index=True)
    confidence = Column(Float, nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    bus_id = Column(Integer, nullable=True)
    camera_id = Column(Integer, nullable=True)
    registration_number = Column(String, nullable=True)
    severity = Column(String, nullable=True)
    status = Column(String, default="new")
    event_metadata = Column(Text, nullable=True)
