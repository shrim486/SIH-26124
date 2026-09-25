from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

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


# ============================================================
# GOVERNMENT LOGIN
# ============================================================

class GovernmentLoginRequest(BaseModel):
    username: str
    password: str


@router.options("/login")
def government_login_options():
    return {}


@router.post("/login")
def government_login(data: GovernmentLoginRequest):

    if not verify_government_credentials(
        data.username,
        data.password,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid government credentials",
        )

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
    from app.services.event_service import get_fleet

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
    return result


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