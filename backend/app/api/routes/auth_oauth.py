"""OAuth 2.0 authentication routes for Google and GitHub.

Flow:
1. Frontend navigates to ``/api/auth/google`` or ``/api/auth/github``.
2. User is redirected to the provider's consent screen.
3. Provider redirects back to ``/api/auth/{provider}/callback``.
4. We exchange the code for tokens, fetch the user profile, upsert the
   ``User`` row, mint a JWT, and redirect the browser to
   ``{FRONTEND_URL}/auth/callback?token={jwt}``.
"""
from __future__ import annotations

import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession

from jose import jwt

from app.config import settings
from app.db.database import get_db
from app.models.user import User
from app.api.auth import get_current_user

router = APIRouter(tags=["auth"])

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_JWT_ALGORITHM = "HS256"
_JWT_EXPIRE_DAYS = 30

# Google endpoints
_GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
_GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
_GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

# GitHub endpoints
_GITHUB_AUTH_URL = "https://github.com/login/oauth/authorize"
_GITHUB_TOKEN_URL = "https://github.com/login/oauth/access_token"
_GITHUB_USER_URL = "https://api.github.com/user"
_GITHUB_EMAILS_URL = "https://api.github.com/user/emails"

# ---------------------------------------------------------------------------
# Response schemas
# ---------------------------------------------------------------------------


class UserResponse(BaseModel):
    id: str
    email: str
    display_name: str
    avatar_url: str | None
    provider: str
    is_premium: bool
    agent_slots: int
    created_at: datetime
    last_login: datetime

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _create_user_jwt(user: User) -> str:
    """Create a JWT token for an authenticated user."""
    now = datetime.now(timezone.utc)
    payload = {
        "sub": str(user.id),
        "email": user.email,
        "type": "user",
        "iat": now,
        "exp": now + timedelta(days=_JWT_EXPIRE_DAYS),
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=_JWT_ALGORITHM)


async def _upsert_user(
    db: AsyncSession,
    *,
    email: str,
    display_name: str,
    avatar_url: str | None,
    provider: str,
    provider_id: str,
) -> User:
    """Find an existing user by provider+provider_id, or create a new one.

    If the user already exists we update ``last_login``, ``display_name``,
    and ``avatar_url`` (profiles may change on the provider side).
    """
    result = await db.execute(
        select(User).where(
            and_(User.provider == provider, User.provider_id == provider_id)
        )
    )
    user = result.scalar_one_or_none()

    now = datetime.now(timezone.utc)

    if user is not None:
        # Returning user -- refresh metadata.
        user.last_login = now
        user.display_name = display_name
        if avatar_url:
            user.avatar_url = avatar_url
        await db.commit()
        await db.refresh(user)
        return user

    # New user.
    user = User(
        id=uuid.uuid4(),
        email=email,
        display_name=display_name,
        avatar_url=avatar_url,
        provider=provider,
        provider_id=str(provider_id),
        is_premium=False,
        agent_slots=settings.MAX_AGENTS_PER_USER_FREE,
        created_at=now,
        last_login=now,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


def _frontend_redirect(token: str) -> RedirectResponse:
    """Redirect the browser to the frontend callback page with the JWT."""
    url = f"{settings.FRONTEND_URL}/auth/callback?token={token}"
    return RedirectResponse(url=url)


def _frontend_error_redirect(error: str) -> RedirectResponse:
    """Redirect the browser to the frontend with an error message."""
    url = f"{settings.FRONTEND_URL}/auth/callback?error={error}"
    return RedirectResponse(url=url)


# ---------------------------------------------------------------------------
# Google OAuth
# ---------------------------------------------------------------------------


@router.get("/auth/google")
async def google_login():
    """Redirect to Google's OAuth 2.0 consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="Google OAuth is not configured",
        )

    params = {
        "client_id": settings.GOOGLE_CLIENT_ID,
        "redirect_uri": f"{settings.OAUTH_REDIRECT_BASE}/api/auth/google/callback",
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    return RedirectResponse(url=f"{_GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/google/callback")
async def google_callback(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth callback from Google."""
    if error:
        return _frontend_error_redirect(error)
    if code is None:
        return _frontend_error_redirect("missing_code")

    # 1. Exchange authorization code for tokens.
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            _GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": f"{settings.OAUTH_REDIRECT_BASE}/api/auth/google/callback",
                "grant_type": "authorization_code",
            },
            headers={"Accept": "application/json"},
        )

    if token_resp.status_code != 200:
        return _frontend_error_redirect("token_exchange_failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return _frontend_error_redirect("no_access_token")

    # 2. Fetch user info.
    async with httpx.AsyncClient() as client:
        userinfo_resp = await client.get(
            _GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_resp.status_code != 200:
        return _frontend_error_redirect("userinfo_failed")

    userinfo = userinfo_resp.json()
    google_id = userinfo.get("id")
    email = userinfo.get("email")
    name = userinfo.get("name", email)
    picture = userinfo.get("picture")

    if not google_id or not email:
        return _frontend_error_redirect("incomplete_profile")

    # 3. Upsert user and mint JWT.
    user = await _upsert_user(
        db,
        email=email,
        display_name=name,
        avatar_url=picture,
        provider="google",
        provider_id=str(google_id),
    )

    jwt_token = _create_user_jwt(user)
    return _frontend_redirect(jwt_token)


# ---------------------------------------------------------------------------
# GitHub OAuth
# ---------------------------------------------------------------------------


@router.get("/auth/github")
async def github_login():
    """Redirect to GitHub's OAuth consent screen."""
    if not settings.GITHUB_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GitHub OAuth is not configured",
        )

    params = {
        "client_id": settings.GITHUB_CLIENT_ID,
        "redirect_uri": f"{settings.OAUTH_REDIRECT_BASE}/api/auth/github/callback",
        "scope": "read:user user:email",
    }
    return RedirectResponse(url=f"{_GITHUB_AUTH_URL}?{urlencode(params)}")


@router.get("/auth/github/callback")
async def github_callback(
    code: str | None = None,
    error: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    """Handle the OAuth callback from GitHub."""
    if error:
        return _frontend_error_redirect(error)
    if code is None:
        return _frontend_error_redirect("missing_code")

    # 1. Exchange authorization code for an access token.
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            _GITHUB_TOKEN_URL,
            data={
                "client_id": settings.GITHUB_CLIENT_ID,
                "client_secret": settings.GITHUB_CLIENT_SECRET,
                "code": code,
                "redirect_uri": f"{settings.OAUTH_REDIRECT_BASE}/api/auth/github/callback",
            },
            headers={"Accept": "application/json"},
        )

    if token_resp.status_code != 200:
        return _frontend_error_redirect("token_exchange_failed")

    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return _frontend_error_redirect("no_access_token")

    # 2. Fetch user profile.
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
    }

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(_GITHUB_USER_URL, headers=headers)

    if user_resp.status_code != 200:
        return _frontend_error_redirect("user_fetch_failed")

    gh_user = user_resp.json()
    github_id = gh_user.get("id")
    name = gh_user.get("name") or gh_user.get("login", "")
    avatar = gh_user.get("avatar_url")
    email = gh_user.get("email")

    # GitHub may not include email in the profile response if it is private.
    # In that case, fetch from the emails endpoint.
    if not email:
        async with httpx.AsyncClient() as client:
            emails_resp = await client.get(_GITHUB_EMAILS_URL, headers=headers)

        if emails_resp.status_code == 200:
            emails = emails_resp.json()
            # Prefer the primary verified email.
            primary = next(
                (e for e in emails if e.get("primary") and e.get("verified")),
                None,
            )
            if primary:
                email = primary["email"]
            elif emails:
                # Fall back to any verified email.
                verified = next(
                    (e for e in emails if e.get("verified")), None
                )
                if verified:
                    email = verified["email"]
                else:
                    email = emails[0].get("email")

    if not github_id or not email:
        return _frontend_error_redirect("incomplete_profile")

    # 3. Upsert user and mint JWT.
    user = await _upsert_user(
        db,
        email=email,
        display_name=name,
        avatar_url=avatar,
        provider="github",
        provider_id=str(github_id),
    )

    jwt_token = _create_user_jwt(user)
    return _frontend_redirect(jwt_token)


# ---------------------------------------------------------------------------
# Authenticated endpoints
# ---------------------------------------------------------------------------


@router.get("/auth/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)):
    """Return the currently authenticated user's profile."""
    return UserResponse(
        id=str(user.id),
        email=user.email,
        display_name=user.display_name,
        avatar_url=user.avatar_url,
        provider=user.provider,
        is_premium=user.is_premium,
        agent_slots=user.agent_slots,
        created_at=user.created_at,
        last_login=user.last_login,
    )


@router.post("/auth/logout", status_code=status.HTTP_200_OK)
async def logout(user: User = Depends(get_current_user)):
    """Logout endpoint.

    JWT tokens are stateless, so there is nothing to invalidate server-side.
    The frontend should discard the token. This endpoint exists so the
    frontend has a canonical URL to call and can be extended later with
    token-blacklist logic if needed.
    """
    return {"detail": "Logged out successfully"}
