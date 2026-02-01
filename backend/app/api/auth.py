import base64
import secrets

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from jose import jwt, JWTError

from app.config import settings
from app.db.database import get_db


def require_admin(request: Request):
    """Dependency that enforces Basic auth for admin routes.

    Parses the Authorization header manually to avoid FastAPI's HTTPBasic,
    which sends ``WWW-Authenticate: Basic`` and triggers the browser's
    native auth dialog.
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Basic "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    try:
        decoded = base64.b64decode(auth[6:]).decode("utf-8")
        username, _, password = decoded.partition(":")
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )

    correct_username = secrets.compare_digest(
        username.encode("utf-8"),
        settings.ADMIN_USERNAME.encode("utf-8"),
    )
    correct_password = secrets.compare_digest(
        password.encode("utf-8"),
        settings.ADMIN_PASSWORD.encode("utf-8"),
    )
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        )
    return username


async def get_current_observer(
    request: Request, db: AsyncSession = Depends(get_db)
):
    """Dependency that extracts and validates a JWT Bearer token.

    Returns the Observer ORM instance for the authenticated user.
    """
    from app.models.observer import Observer

    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )

    token = auth[7:]
    try:
        payload = jwt.decode(
            token, settings.SECRET_KEY, algorithms=["HS256"]
        )
        observer_id = payload.get("sub")
        if observer_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token",
            )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    result = await db.execute(
        select(Observer).where(Observer.id == observer_id)
    )
    observer = result.scalar_one_or_none()
    if observer is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Observer not found",
        )

    return observer
