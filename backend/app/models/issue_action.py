from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from app.db.database import Base


class IssueAction(Base):
    __tablename__ = 'issue_actions'
    id = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey('events.id'), index=True, nullable=False)
    previous_status = Column(String, nullable=False)
    status = Column(String, nullable=False)
    note = Column(String(1000), nullable=False, default='')
    actor = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
