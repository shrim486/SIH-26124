from sqlalchemy import Column, Integer, String, Float, DateTime
from datetime import datetime
from app.db.database import Base


class Alert(Base):
    __tablename__ = "alerts"

    id = Column(Integer, primary_key=True, index=True)

    alert_type = Column(String, nullable=False)

    message = Column(String, nullable=False)

    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)

    severity = Column(String, nullable=True)

    issue_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    expires_at = Column(DateTime, nullable=True)