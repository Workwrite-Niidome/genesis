import base64
import secrets

from fastapi import Depends, HTTPException, Request, status

from app.config import settings


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
