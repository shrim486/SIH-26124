from sqlalchemy import Column, Integer, String, Boolean
from app.db.database import Base


class Bus(Base):
    __tablename__ = "buses"

    id = Column(Integer, primary_key=True, index=True)
    bus_number = Column(String, unique=True, nullable=False)
    route_number = Column(String, nullable=True)
    is_active = Column(Boolean, default=True)