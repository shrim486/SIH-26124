"""Stable association between a map event and a detected video segment."""

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, Integer, String
from app.db.database import Base


class AnalysisIncident(Base):
    __tablename__ = "analysis_incidents"
    id = Column(Integer, primary_key=True)
    source_key = Column(String(100), unique=True, nullable=False, index=True)
    event_id = Column(Integer, ForeignKey("events.id"), nullable=False, index=True)
    run_id = Column(String(24), nullable=False)
    segment_id = Column(String(40), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
