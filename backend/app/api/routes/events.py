from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db.database import get_db
from app.schemas.event import EventCreate
from app.services.event_service import create_event


router = APIRouter(prefix="/events", tags=["events"])


@router.post("", status_code=status.HTTP_200_OK)
@router.post("/", status_code=status.HTTP_200_OK)
@router.post("/ingest", status_code=status.HTTP_200_OK)
def ingest_event(
    data: EventCreate,
    db: Session = Depends(get_db),
):
    result = create_event(db, data)

    if result is None:
        raise HTTPException(status_code=500, detail="Event processing failed")

    return {
        "success": True,
        "category": result["category"],
        "duplicate": result.get("duplicate", False),
        "event_id": result["event"].id,
        "status": result["event"].status,
        "message": "Event processed successfully",
    }


@router.get("/")
def get_events(db: Session = Depends(get_db)):
    from app.models.event import Event

    events = db.query(Event).order_by(Event.timestamp.desc()).limit(100).all()
    return events
