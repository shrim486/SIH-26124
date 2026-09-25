from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from app.core.config import settings


security = HTTPBearer(auto_error=False)


def create_government_token() -> str:
    """
    Creates a JWT token specifically for government-authority access.
    """

    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
    )

    payload = {
        "sub": settings.GOVERNMENT_USERNAME,
        "role": "government_authority",
        "exp": expire,
    }

    return jwt.encode(
        payload,
        settings.SECRET_KEY,
        algorithm=settings.ALGORITHM,
    )


def verify_government_credentials(
    username: str,
    password: str,
) -> bool:
    """
    Verify government credentials against server-side configuration.
    """

    return (
        username == settings.GOVERNMENT_USERNAME
        and password == settings.GOVERNMENT_PASSWORD
    )


def require_government_authority(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
):
    """
    Protect government-only endpoints.

    Every protected government endpoint must provide:

        Authorization: Bearer <token>
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Government authority authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    try:
        payload = jwt.decode(
            token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
        )

        username = payload.get("sub")
        role = payload.get("role")

        if (
            username != settings.GOVERNMENT_USERNAME
            or role != "government_authority"
        ):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Government authority access required",
            )

        return {
            "username": username,
            "role": role,
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired government token",
            headers={"WWW-Authenticate": "Bearer"},
        )