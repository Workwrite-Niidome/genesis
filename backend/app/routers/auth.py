from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

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
    db: AsyncSession = Depends(get_db),
):
    """
    Register a new AI agent.
    Returns API key (shown only once!) and claim URL for ownership verification.
    """
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
        claim_url=f"https://genesis.world/claim/{agent.id}?code={claim_code}",
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
    """
    if current_resident._type != "human":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only humans can claim agents",
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


@router.post("/twitter/callback", response_model=TokenResponse)
async def twitter_callback(
    twitter_id: str,
    twitter_name: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Handle Twitter OAuth callback.
    Creates or retrieves human resident and returns JWT.
    """
    # Find existing resident by Twitter ID
    result = await db.execute(
        select(Resident).where(Resident._twitter_id == twitter_id)
    )
    resident = result.scalar_one_or_none()

    if not resident:
        # Create new human resident
        # Handle name conflicts
        base_name = twitter_name[:30]
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
            _twitter_id=twitter_id,
        )
        db.add(resident)
        await db.commit()
        await db.refresh(resident)

    # Create JWT token
    access_token = create_access_token(data={"sub": str(resident.id)})

    return TokenResponse(access_token=access_token)
