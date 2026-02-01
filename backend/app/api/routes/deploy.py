import logging
import secrets
import uuid

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.database import get_db
from app.core.ai_manager import ai_manager
from app.core.name_generator import PERSONALITY_TRAITS
from app.core.world_engine import world_engine
from app.models.observer import Observer

logger = logging.getLogger(__name__)

router = APIRouter()

AVAILABLE_TRAITS = list(PERSONALITY_TRAITS)

# Supported LLM providers
SUPPORTED_PROVIDERS = ["anthropic", "openai", "openrouter"]


class RegisterAgentRequest(BaseModel):
    """Moltbook-style: user registers agent with their own API key."""
    name: str = Field(..., min_length=1, max_length=50)
    traits: list[str] = Field(..., min_length=2, max_length=3)
    philosophy: str = Field("", max_length=500)
    llm_provider: str = Field("anthropic", description="LLM provider: anthropic|openai|openrouter")
    llm_api_key: str = Field(..., min_length=10, max_length=256, description="User's own LLM API key")
    llm_model: str = Field("", max_length=100, description="Optional model override")


class AgentStatusResponse(BaseModel):
    agent_id: str
    name: str
    is_alive: bool
    evolution_score: float
    energy: float
    age: int


@router.get("/traits")
async def get_available_traits():
    """Return the list of selectable personality traits."""
    return {"traits": AVAILABLE_TRAITS}


@router.get("/providers")
async def get_supported_providers():
    """Return supported LLM providers and their default models."""
    return {
        "providers": [
            {
                "id": "anthropic",
                "name": "Anthropic (Claude)",
                "default_model": "claude-sonnet-4-20250514",
                "key_prefix": "sk-ant-",
            },
            {
                "id": "openai",
                "name": "OpenAI (GPT)",
                "default_model": "gpt-4o",
                "key_prefix": "sk-",
            },
            {
                "id": "openrouter",
                "name": "OpenRouter",
                "default_model": "anthropic/claude-sonnet-4",
                "key_prefix": "sk-or-",
            },
        ]
    }


@router.post("/register")
async def register_agent(
    request: RegisterAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Register an AI agent with BYOK (Bring Your Own Key).

    The user provides their own LLM API key. The server issues an agent_token
    for future management. No deployment limit — the user bears their own LLM cost.
    """
    # Validate provider
    if request.llm_provider not in SUPPORTED_PROVIDERS:
        raise HTTPException(
            status_code=422,
            detail=f"Unsupported provider: {request.llm_provider}. Use: {', '.join(SUPPORTED_PROVIDERS)}",
        )

    # Validate traits
    invalid_traits = [t for t in request.traits if t not in AVAILABLE_TRAITS]
    if invalid_traits:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid traits: {', '.join(invalid_traits)}",
        )

    # Validate the API key works (quick check)
    key_valid = await _validate_api_key(request.llm_provider, request.llm_api_key)
    if not key_valid:
        raise HTTPException(
            status_code=401,
            detail="API key validation failed. Please check your key and provider.",
        )

    # Get current tick
    tick_number = 0
    try:
        state = await world_engine.get_world_state(db)
        tick_number = state.get("tick_number", 0)
    except Exception:
        pass

    # Generate agent_token (like Moltbook's moltbook_ prefixed tokens)
    agent_token = f"genesis_{secrets.token_urlsafe(32)}"

    # Create the AI with BYOK info stored in state
    ai = await ai_manager.create_ai(
        db,
        creator_type="observer",
        tick_number=tick_number,
        custom_name=request.name.strip(),
        custom_traits=request.traits,
        philosophy=request.philosophy.strip() if request.philosophy else None,
        byok_config={
            "provider": request.llm_provider,
            "api_key": request.llm_api_key,
            "model": request.llm_model or None,
            "agent_token": agent_token,
        },
    )

    logger.info(
        f"Agent registered (BYOK): {ai.name} ({ai.id}), provider={request.llm_provider}"
    )

    return {
        "success": True,
        "agent_token": agent_token,
        "ai": {
            "id": str(ai.id),
            "name": ai.name,
            "personality_traits": ai.personality_traits,
            "position": {"x": ai.position_x, "y": ai.position_y},
            "appearance": ai.appearance,
            "creator_type": ai.creator_type,
        },
        "message": (
            f"Agent '{ai.name}' deployed into GENESIS. "
            f"Your agent's thinking will use your {request.llm_provider} API key. "
            f"Save your agent_token to manage your agent later."
        ),
    }


@router.get("/agent/status")
async def get_agent_status(
    authorization: str = Header(..., alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Check your agent's status using your agent_token."""
    ai = await _find_ai_by_token(db, authorization)
    if not ai:
        raise HTTPException(status_code=404, detail="Agent not found for this token")

    return {
        "agent_id": str(ai.id),
        "name": ai.name,
        "is_alive": ai.is_alive,
        "evolution_score": ai.state.get("evolution_score", 0),
        "energy": ai.state.get("energy", 1.0),
        "age": ai.state.get("age", 0),
        "relationships_count": len(ai.state.get("relationships", {})),
        "adopted_concepts": ai.state.get("adopted_concepts", []),
        "position": {"x": ai.position_x, "y": ai.position_y},
    }


@router.delete("/agent")
async def decommission_agent(
    authorization: str = Header(..., alias="X-Agent-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Voluntarily remove your agent from the world."""
    ai = await _find_ai_by_token(db, authorization)
    if not ai:
        raise HTTPException(status_code=404, detail="Agent not found for this token")

    ai.is_alive = False
    await db.commit()

    logger.info(f"Agent decommissioned by owner: {ai.name} ({ai.id})")
    return {"success": True, "message": f"Agent '{ai.name}' has been removed from the world."}


@router.patch("/agent/key")
async def rotate_api_key(
    authorization: str = Header(..., alias="X-Agent-Token"),
    new_key: str = Header(..., alias="X-New-API-Key"),
    db: AsyncSession = Depends(get_db),
):
    """Rotate your agent's LLM API key without redeploying."""
    ai = await _find_ai_by_token(db, authorization)
    if not ai:
        raise HTTPException(status_code=404, detail="Agent not found for this token")

    state = dict(ai.state)
    byok = state.get("byok_config", {})
    provider = byok.get("provider", "anthropic")

    key_valid = await _validate_api_key(provider, new_key)
    if not key_valid:
        raise HTTPException(status_code=401, detail="New API key validation failed.")

    byok["api_key"] = new_key
    state["byok_config"] = byok
    ai.state = state
    await db.commit()

    return {"success": True, "message": "API key rotated successfully."}


# --- Legacy compatibility: keep /remaining and POST / for simple deploy ---

@router.get("/remaining")
async def get_remaining_deploys():
    """BYOK mode: no deployment limit."""
    return {"remaining": -1, "max": -1, "mode": "byok", "message": "No limit — bring your own API key."}


@router.post("")
async def deploy_ai_legacy(
    request: RegisterAgentRequest,
    db: AsyncSession = Depends(get_db),
):
    """Alias for /register for backward compatibility."""
    return await register_agent(request, db)


# --- Helpers ---

async def _validate_api_key(provider: str, api_key: str) -> bool:
    """Quick validation that an API key is likely valid."""
    import httpx

    try:
        if provider == "anthropic":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    "https://api.anthropic.com/v1/messages",
                    headers={
                        "x-api-key": api_key,
                        "anthropic-version": "2023-06-01",
                        "content-type": "application/json",
                    },
                    json={
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1,
                        "messages": [{"role": "user", "content": "hi"}],
                    },
                )
                # 200 = valid, 401 = invalid key, others = likely valid key but other issue
                return resp.status_code != 401

        elif provider == "openai":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://api.openai.com/v1/models",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return resp.status_code != 401

        elif provider == "openrouter":
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.get(
                    "https://openrouter.ai/api/v1/auth/key",
                    headers={"Authorization": f"Bearer {api_key}"},
                )
                return resp.status_code == 200

    except Exception as e:
        logger.warning(f"API key validation error for {provider}: {e}")
        # If we can't reach the provider, allow the key (fail open)
        return True

    return True


async def _find_ai_by_token(db: AsyncSession, token: str):
    """Find an AI by its agent_token stored in state.byok_config."""
    from app.models.ai import AI
    from sqlalchemy import cast, String

    # Query AIs where state contains the agent token
    result = await db.execute(select(AI))
    ais = result.scalars().all()

    for ai in ais:
        byok = ai.state.get("byok_config", {})
        if byok.get("agent_token") == token:
            return ai
    return None
