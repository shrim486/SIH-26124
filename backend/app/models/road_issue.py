from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.database import Base


class RoadIssue(Base):
    __tablename__ = "road_issues"

    id = Column(Integer, primary_key=True, index=True)

    issue_type = Column(String, nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    confidence = Column(Float, nullable=True)

    severity = Column(String, nullable=True)

    status = Column(String, default="open")

    first_detected = Column(DateTime, default=datetime.utcnow)
    last_detected = Column(DateTime, default=datetime.utcnow)