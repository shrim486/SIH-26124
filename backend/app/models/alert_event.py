"""One in-app alert per detected event, with shared location and evidence."""
from sqlalchemy import Column, ForeignKey, Integer
from app.db.database import Base


class AlertEvent(Base):
    __tablename__ = "alert_events"
    id = Column(Integer, primary_key=True)
    alert_id = Column(Integer, ForeignKey("alerts.id"), nullable=False, unique=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, unique=True)
