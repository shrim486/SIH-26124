from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.database import Base


class Violation(Base):
    __tablename__ = "violations"

    id = Column(Integer, primary_key=True, index=True)

    violation_type = Column(String, nullable=False)

    registration_number = Column(String, nullable=True)

    confidence = Column(Float, nullable=True)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    timestamp = Column(DateTime, default=datetime.utcnow)

    bus_id = Column(Integer, nullable=True)

    status = Column(String, default="pending")