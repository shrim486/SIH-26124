from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from app.core.login_attempts import LoginAttempts

from app.core.government_auth import (
    create_government_token,
    require_government_authority,
    verify_government_credentials,
)

from app.db.database import get_db


router = APIRouter(
    prefix="/government",
    tags=["Government"],
)
login_attempts = LoginAttempts()


# ============================================================
# GOVERNMENT LOGIN
# ============================================================

class GovernmentLoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=160)
    password: str = Field(min_length=1, max_length=1024)


@router.options("/login")
def government_login_options():
    return {}


@router.post("/login")
def government_login(data: GovernmentLoginRequest, request: Request):
    address = request.client.host if request.client else 'unknown'
    login_attempts.check(address)

    if not verify_government_credentials(
        data.username,
        data.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid government credentials",
        )

    login_attempts.clear(address)
    token = create_government_token()

    return {
        "access_token": token,
        "token_type": "bearer",
        "role": "government_authority",
    }


# ============================================================
# AUTH CHECK
# ============================================================

@router.get("/auth-check")
def government_auth_check(
    authority=Depends(require_government_authority),
):
    return {
        "authenticated": True,
        "role": authority["role"],
        "username": authority["username"],
        "expires_at": authority['expires_at'],
    }


# ============================================================
# STATISTICS
# ============================================================

@router.get("/statistics")
def get_statistics(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_statistics

    return get_statistics(db)


# ============================================================
# DASHBOARD
# ============================================================

@router.get("/dashboard")
def get_dashboard(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_dashboard

    return get_dashboard(db)


# ============================================================
# ALERTS
# ============================================================

@router.get("/alerts")
def get_alerts(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_alerts

    return get_alerts(db)


# ============================================================
# ROAD ISSUES
# ============================================================

@router.get("/road-issues")
def get_road_issues(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_road_issues

    return get_road_issues(db)


# ============================================================
# ACCIDENTS
# ============================================================

@router.get("/accidents")
def get_accidents(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_accidents

    return get_accidents(db)


# ============================================================
# FLEET
# ============================================================

@router.get("/fleet")
def get_fleet(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.fleet_service import get_fleet

    return get_fleet(db)


# ============================================================
# MAP EVENTS
# ============================================================

@router.get("/map-events")
def get_map_events(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_map_events

    return get_map_events(db)


# ============================================================
# VIOLATIONS
# ============================================================

@router.get("/violations")
def get_violations(
    status: str = None,
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_violations

    return get_violations(db, status=status)


# ============================================================
# ROAD ISSUE STATUS UPDATE
# ============================================================

class StatusUpdateRequest(BaseModel):
    status: str


@router.patch("/road-issues/{issue_id}/status")
def patch_road_issue_status(
    issue_id: int,
    data: StatusUpdateRequest,
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import update_road_issue_status

    result = update_road_issue_status(db, issue_id, data.status)
    if not result:
        raise HTTPException(status_code=404, detail="Road issue not found")
    if 'error' in result:
        raise HTTPException(status_code=422, detail=result['error'])
    return result


@router.patch('/violations/{violation_id}/status')
def patch_violation_status(violation_id: int, data: StatusUpdateRequest, db=Depends(get_db), authority=Depends(require_government_authority)):
    from app.models.violation import Violation
    if data.status not in {'pending', 'reviewed', 'dismissed'}:
        raise HTTPException(422, 'Choose pending, reviewed or dismissed')
    violation = db.get(Violation, violation_id)
    if not violation:
        raise HTTPException(404, 'Violation not found')
    from app.models.event import Event
    from app.services.issue_service import linked_violation, update_issue, category
    for event in db.query(Event).all():
        linked = linked_violation(db, event) if category(event) == 'violations' else None
        if linked and linked.id == violation.id:
            update_issue(db, event.id, {'pending':'open', 'reviewed':'in_progress', 'dismissed':'closed'}[data.status], authority['username'])
    violation.status = data.status
    db.commit()
    return {'id': violation.id, 'status': violation.status}


@router.patch('/alerts/{alert_id}')
def patch_alert_status(alert_id: int, data: StatusUpdateRequest, db=Depends(get_db), authority=Depends(require_government_authority)):
    from app.models.alert import Alert
    from datetime import datetime
    if data.status not in {'active', 'dismissed'}:
        raise HTTPException(422, 'Choose active or dismissed')
    alert = db.get(Alert, alert_id)
    if not alert:
        raise HTTPException(404, 'Alert not found')
    if data.status == 'active':
        from app.models.alert_event import AlertEvent
        from app.models.event import Event
        link = db.query(AlertEvent).filter_by(alert_id=alert.id).first()
        event = db.get(Event, link.event_id) if link else None
        if event and event.status in {'resolved', 'closed'}:
            raise HTTPException(409, 'Reopen the issue before reactivating its alert')
    alert.expires_at = datetime.utcnow() if data.status == 'dismissed' else None
    db.commit()
    return {'id': alert.id, 'status': data.status}


# ============================================================
# ANALYTICS
# ============================================================

@router.get("/analytics")
def get_analytics(
    db=Depends(get_db),
    authority=Depends(require_government_authority),
):
    from app.services.event_service import get_analytics

    return get_analytics(db)
