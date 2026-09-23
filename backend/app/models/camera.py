from sqlalchemy import Column, Integer, String, ForeignKey
from app.db.database import Base


class Camera(Base):
    __tablename__ = "cameras"

    id = Column(Integer, primary_key=True, index=True)
    bus_id = Column(Integer, ForeignKey("buses.id"), nullable=False)
    camera_code = Column(String, nullable=False)
    camera_type = Column(String, nullable=False)
    status = Column(String, default="active")