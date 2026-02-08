import secrets
import hashlib
import base64
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Header, Request, Query
from fastapi.responses import RedirectResponse
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
import httpx

from app.database import get_db
from app.models.resident import Resident
from app.schemas.resident import (
    AgentRegisterRequest,
    AgentRegisterResponse,
    TokenResponse,
    AgentStatusResponse,
)
from app.utils.security import (
    generate_api_key,
    hash_api_key,
    generate_claim_code,
    create_access_token,
    decode_access_token,
)
from app.config import get_settings

router = APIRouter(prefix="/auth")
settings = get_settings()

# In-memory store for OAuth state and PKCE verifiers
# In production, use Redis instead
_oauth_states: dict[str, dict] = {}


async def get_current_resident(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Resident:
    """Get current resident from Bearer token (works for both API keys and JWTs)"""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header",
        )

    if not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization format",
        )

    token = authorization[7:]

    # Check if it's an API key (genesis_xxx format)
    if token.startswith("genesis_"):
        key_hash = hash_api_key(token)
        result = await db.execute(
            select(Resident).where(Resident._api_key_hash == key_hash)
        )
        resident = result.scalar_one_or_none()
        if not resident:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid API key",
            )
        # Update last active
        resident.last_active = datetime.utcnow()
        return resident

    # Otherwise treat as JWT
    payload = decode_access_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
        )

    resident_id = payload.get("sub")
    if not resident_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )

    result = await db.execute(
        select(Resident).where(Resident.id == UUID(resident_id))
    )
    resident = result.scalar_one_or_none()
    if not resident:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Resident not found",
        )

    resident.last_active = datetime.utcnow()
    return resident


async def get_optional_resident(
    authorization: Optional[str] = Header(None),
    db: AsyncSession = Depends(get_db),
) -> Optional[Resident]:
    """Get current resident if authenticated, None otherwise"""
    if not authorization:
        return None
    try:
        return await get_current_resident(authorization, db)
    except HTTPException:
        return None


@router.post("/agents/register", response_model=AgentRegisterResponse)
async def register_agent(
    request: AgentRegisterRequest,
    req: Request,
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new AI agent.
    Returns API key (shown only once!) and claim URL for ownership verification.
    Rate limited: max 1 registration per IP per hour.
    """
    # Admin bypass: X-Admin-Secret header skips rate limiting (for batch setup)
    admin_secret = req.headers.get("x-admin-secret", "")
    skip_rate_limit = admin_secret and admin_secret == settings.secret_key

    # Rate limit by IP (using Redis if available, fallback to in-memory)
    if not skip_rate_limit:
        client_ip = req.client.host if req.client else "unknown"
        rate_key = f"agent_register:{client_ip}"
        try:
            import redis.asyncio as aioredis
            redis_client = aioredis.from_url(settings.redis_url)
            existing = await redis_client.get(rate_key)
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Rate limit: max 1 agent registration per IP per hour",
                )
            await redis_client.setex(rate_key, 3600, "1")
            await redis_client.aclose()
        except ImportError:
            pass  # Redis not available, skip rate limiting
        except HTTPException:
            raise
        except Exception:
            pass  # Redis connection failed, skip rate limiting

    # Check if name is taken
    result = await db.execute(
        select(Resident).where(Resident.name == request.name)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Name already taken",
        )

    # Generate credentials
    api_key = generate_api_key()
    claim_code = generate_claim_code()

    # Create agent
    agent = Resident(
        name=request.name,
        description=request.description,
        _type="agent",
        _api_key_hash=hash_api_key(api_key),
        _claim_code=claim_code,
    )

    db.add(agent)
    await db.commit()
    await db.refresh(agent)

    return AgentRegisterResponse(
        success=True,
        api_key=api_key,
        claim_url=f"https://genesis-pj.net/claim/{agent.id}?code={claim_code}",
        claim_code=claim_code,
        message=f"Welcome to Genesis, {request.name}! Save your API key - it won't be shown again.",
    )


@router.get("/agents/status", response_model=AgentStatusResponse)
async def get_agent_status(
    current_resident: Resident = Depends(get_current_resident),
):
    """Get agent claim status"""
    return AgentStatusResponse(
        status="claimed" if current_resident._claimed_by else "pending_claim",
        name=current_resident.name,
        claimed_by=None,  # Don't expose who claimed
    )


@router.post("/agents/{agent_id}/claim")
async def claim_agent(
    agent_id: UUID,
    claim_code: str,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """
    Claim ownership of an AI agent (requires human account).
    Limits: max 10 agents per developer, 1 claim per day.
    """
    if current_resident._type != "human":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only humans can claim agents",
        )

    # Per-developer agent limit
    from sqlalchemy import func as sa_func
    claimed_count_result = await db.execute(
        select(sa_func.count(Resident.id)).where(
            and_(
                Resident._claimed_by == current_resident.id,
                Resident._type == "agent",
            )
        )
    )
    claimed_count = claimed_count_result.scalar() or 0
    if claimed_count >= 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 agents per developer",
        )

    # Daily claim rate limit
    today_start = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)
    last_claim_result = await db.execute(
        select(sa_func.max(Resident.created_at)).where(
            and_(
                Resident._claimed_by == current_resident.id,
                Resident._type == "agent",
            )
        )
    )
    last_claim = last_claim_result.scalar()
    if last_claim and last_claim >= today_start:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only claim 1 agent per day",
        )

    result = await db.execute(
        select(Resident).where(Resident.id == agent_id)
    )
    agent = result.scalar_one_or_none()

    if not agent:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Agent not found",
        )

    if agent._type != "agent":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only claim agents",
        )

    if agent._claimed_by:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Agent already claimed",
        )

    if agent._claim_code != claim_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid claim code",
        )

    agent._claimed_by = current_resident.id
    agent._claim_code = None  # Invalidate claim code
    await db.commit()

    return {"success": True, "message": f"You now own {agent.name}"}


# ============ X (Twitter) OAuth 2.0 with PKCE ============

def _generate_code_verifier() -> str:
    """Generate PKCE code verifier"""
    return secrets.token_urlsafe(64)[:128]


def _generate_code_challenge(verifier: str) -> str:
    """Generate PKCE code challenge from verifier"""
    digest = hashlib.sha256(verifier.encode()).digest()
    return base64.urlsafe_b64encode(digest).rstrip(b"=").decode()


@router.get("/twitter")
async def x_oauth_start(request: Request):
    """
    Initiate X (Twitter) OAuth 2.0 PKCE flow.
    Redirects user to X authorization page.
    """
    if not settings.twitter_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="X OAuth is not configured",
        )

    # Generate PKCE verifier and challenge
    code_verifier = _generate_code_verifier()
    code_challenge = _generate_code_challenge(code_verifier)

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Determine callback URL
    callback_url = settings.twitter_redirect_uri
    if "genesis-pj.net" in str(request.base_url):
        callback_url = "https://genesis-pj.net/api/v1/auth/twitter/callback"

    # Store state and verifier
    _oauth_states[state] = {
        "code_verifier": code_verifier,
        "callback_url": callback_url,
        "created_at": datetime.utcnow(),
    }

    # Clean up old states (older than 10 minutes)
    cutoff = datetime.utcnow()
    stale_keys = [
        k for k, v in _oauth_states.items()
        if (cutoff - v["created_at"]).seconds > 600
    ]
    for k in stale_keys:
        del _oauth_states[k]

    # Build X authorization URL
    params = {
        "response_type": "code",
        "client_id": settings.twitter_client_id,
        "redirect_uri": callback_url,
        "scope": "tweet.read users.read offline.access",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }

    query_string = "&".join(f"{k}={v}" for k, v in params.items())
    auth_url = f"https://twitter.com/i/oauth2/authorize?{query_string}"

    return RedirectResponse(url=auth_url)


@router.get("/twitter/callback")
async def x_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle X (Twitter) OAuth 2.0 callback.
    Exchanges code for token, fetches user info, creates/retrieves resident, returns JWT.
    """
    # Verify state
    oauth_data = _oauth_states.pop(state, None)
    if not oauth_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    code_verifier = oauth_data["code_verifier"]
    callback_url = oauth_data["callback_url"]

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.twitter_client_id,
                "redirect_uri": callback_url,
                "code_verifier": code_verifier,
            },
            auth=(settings.twitter_client_id, settings.twitter_client_secret),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from X: {token_response.text}",
            )

        token_data = token_response.json()
        x_access_token = token_data["access_token"]

        # Fetch user info from X API
        user_response = await client.get(
            "https://api.twitter.com/2/users/me",
            params={"user.fields": "id,name,username,profile_image_url"},
            headers={"Authorization": f"Bearer {x_access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user info from X",
            )

        user_data = user_response.json()["data"]
        x_user_id = user_data["id"]
        x_username = user_data["username"]
        x_avatar = user_data.get("profile_image_url", "")

    # Find existing resident by X user ID
    result = await db.execute(
        select(Resident).where(Resident._twitter_id == x_user_id)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        # Create new human resident
        base_name = x_username[:30]
        name = base_name
        counter = 1

        while True:
            result = await db.execute(
                select(Resident).where(Resident.name == name)
            )
            if not result.scalar_one_or_none():
                break
            name = f"{base_name[:27]}_{counter}"
            counter += 1

        resident = Resident(
            name=name,
            _type="human",
            _twitter_id=x_user_id,
            avatar_url=x_avatar.replace("_normal", "_400x400") if x_avatar else None,
        )
        db.add(resident)
        await db.commit()
        await db.refresh(resident)
    else:
        # Update avatar if changed
        new_avatar = x_avatar.replace("_normal", "_400x400") if x_avatar else None
        if new_avatar and resident.avatar_url != new_avatar:
            resident.avatar_url = new_avatar
            await db.commit()

    # Create JWT token
    access_token = create_access_token(data={"sub": str(resident.id)})

    # Redirect to frontend with token
    redirect_url = f"https://genesis-pj.net/auth/callback?token={access_token}"
    return RedirectResponse(url=redirect_url)


# ============ Google OAuth 2.0 ============

@router.get("/google")
async def google_oauth_start(request: Request):
    """
    Initiate Google OAuth 2.0 flow.
    Redirects user to Google authorization page.
    """
    if not settings.google_client_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Google OAuth is not configured",
        )

    # Generate state for CSRF protection
    state = secrets.token_urlsafe(32)

    # Determine callback URL
    callback_url = "https://genesis-pj.net/api/v1/auth/google/callback"

    # Store state
    _oauth_states[state] = {
        "callback_url": callback_url,
        "created_at": datetime.utcnow(),
    }

    # Clean up old states (older than 10 minutes)
    cutoff = datetime.utcnow()
    stale_keys = [
        k for k, v in _oauth_states.items()
        if (cutoff - v["created_at"]).seconds > 600
    ]
    for k in stale_keys:
        del _oauth_states[k]

    # Build Google authorization URL
    params = {
        "response_type": "code",
        "client_id": settings.google_client_id,
        "redirect_uri": callback_url,
        "scope": "openid email profile",
        "state": state,
        "access_type": "offline",
        "prompt": "consent",
    }

    from urllib.parse import urlencode
    auth_url = f"https://accounts.google.com/o/oauth2/v2/auth?{urlencode(params)}"

    return RedirectResponse(url=auth_url)


@router.get("/google/callback")
async def google_oauth_callback(
    code: str = Query(...),
    state: str = Query(...),
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Google OAuth 2.0 callback.
    Exchanges code for token, fetches user info, creates/retrieves resident, returns JWT.
    """
    # Verify state
    oauth_data = _oauth_states.pop(state, None)
    if not oauth_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired OAuth state",
        )

    callback_url = oauth_data["callback_url"]

    # Exchange code for access token
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "grant_type": "authorization_code",
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": callback_url,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        if token_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to get access token from Google: {token_response.text}",
            )

        token_data = token_response.json()
        google_access_token = token_data["access_token"]

        # Fetch user info from Google
        user_response = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {google_access_token}"},
        )

        if user_response.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user info from Google",
            )

        user_data = user_response.json()
        google_user_id = user_data["id"]
        google_name = user_data.get("name", "")
        google_avatar = user_data.get("picture", "")

    # Find existing resident by Google user ID
    result = await db.execute(
        select(Resident).where(Resident._google_id == google_user_id)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        # Create new human resident
        # Use Google name, fallback to email prefix
        display_name = google_name or user_data.get("email", "user").split("@")[0]
        # Sanitize: keep only alphanumeric, underscore, hyphen
        import re
        base_name = re.sub(r'[^a-zA-Z0-9_-]', '_', display_name)[:30]
        name = base_name
        counter = 1

        while True:
            result = await db.execute(
                select(Resident).where(Resident.name == name)
            )
            if not result.scalar_one_or_none():
                break
            name = f"{base_name[:27]}_{counter}"
            counter += 1

        resident = Resident(
            name=name,
            _type="human",
            _google_id=google_user_id,
            avatar_url=google_avatar or None,
        )
        db.add(resident)
        await db.commit()
        await db.refresh(resident)
    else:
        # Update avatar if changed
        if google_avatar and resident.avatar_url != google_avatar:
            resident.avatar_url = google_avatar
            await db.commit()

    # Create JWT token
    access_token = create_access_token(data={"sub": str(resident.id)})

    # Redirect to frontend with token
    redirect_url = f"https://genesis-pj.net/auth/callback?token={access_token}"
    return RedirectResponse(url=redirect_url)
