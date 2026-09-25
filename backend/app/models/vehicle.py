from sqlalchemy import Column, Integer, String
from app.db.database import Base


class Vehicle(Base):
    __tablename__ = "vehicles"

    id = Column(Integer, primary_key=True, index=True)
    registration_number = Column(String, unique=True, index=True, nullable=False)
    vehicle_type = Column(String, nullable=True)