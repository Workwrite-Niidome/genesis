"""
Phantom Night — Werewolf Game API Endpoints
"""
from datetime import datetime
from typing import Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.resident import Resident
from app.models.werewolf_game import (
    WerewolfGame, WerewolfRole, NightAction, DayVote, WerewolfGameEvent, ROLES,
)
from app.schemas.werewolf import (
    GameResponse, MyRoleResponse, PlayerInfo,
    NightActionRequest, NightActionResponse,
    CreateLobbyRequest, LobbyResponse,
    DayVoteRequest, DayVoteResponse, DayVotesResponse, VoteTallyEntry, VoteDetail,
    EventResponse, EventList,
    PhantomChatRequest, PhantomChatMessage, PhantomChatResponse,
    GameListResponse,
)
from app.services.werewolf_game import (
    get_current_game, get_player_role, get_alive_players, get_all_players,
    get_phantom_teammates, get_lobby_players,
    create_lobby, join_lobby, leave_lobby, start_game_from_lobby,
    submit_phantom_attack, submit_oracle_investigation, submit_guardian_protection,
    submit_debugger_identify,
    submit_day_vote, get_vote_tally, get_votes_for_round,
    get_game_events, get_game_history,
)
from app.routers.auth import get_current_resident, get_optional_resident

router = APIRouter(prefix="/werewolf")


# ═══════════════════════════════════════════════════════════════════════════
# LOBBY / MATCHMAKING
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/lobby/create", response_model=LobbyResponse)
async def create_game_lobby(
    data: CreateLobbyRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a new game lobby. You are automatically joined."""
    try:
        game = await create_lobby(
            db, current_resident.id, data.max_players,
            data.day_duration_hours, data.night_duration_hours,
        )
        return await _build_lobby_response(db, game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lobby", response_model=Optional[LobbyResponse])
async def get_lobby(
    db: AsyncSession = Depends(get_db),
):
    """Get the current lobby state (if a lobby is active)."""
    game = await get_current_game(db)
    if not game or game.status != "preparing":
        return None
    return await _build_lobby_response(db, game)


@router.post("/lobby/join", response_model=LobbyResponse)
async def join_game_lobby(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Join the current active lobby."""
    game = await get_current_game(db)
    if not game or game.status != "preparing":
        raise HTTPException(status_code=400, detail="No active lobby")

    try:
        await join_lobby(db, game.id, current_resident.id)
        return await _build_lobby_response(db, game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lobby/leave", response_model=dict)
async def leave_game_lobby(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Leave the current lobby."""
    game = await get_current_game(db)
    if not game or game.status != "preparing":
        raise HTTPException(status_code=400, detail="No active lobby")

    try:
        await leave_lobby(db, game.id, current_resident.id)
        return {"success": True, "message": "Left the lobby"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/lobby/start", response_model=GameResponse)
async def start_game_from_lobby_endpoint(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Start the game from the lobby. AI agents fill remaining slots."""
    game = await get_current_game(db)
    if not game or game.status != "preparing":
        raise HTTPException(status_code=400, detail="No active lobby")

    # Only the creator or any player can start
    try:
        game = await start_game_from_lobby(db, game.id)
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


async def _build_lobby_response(db: AsyncSession, game: WerewolfGame) -> LobbyResponse:
    """Build a LobbyResponse with player info."""
    players = await get_lobby_players(db, game.id)
    human_count = sum(1 for p in players if p.resident and p.resident._type == "human")
    ai_count = sum(1 for p in players if p.resident and p.resident._type == "agent")
    max_humans = (game.max_players or 0) // 2

    joined = []
    for p in players:
        if p.resident:
            joined.append(PlayerInfo(
                id=p.resident.id,
                name=p.resident.name,
                avatar_url=p.resident.avatar_url,
                karma=p.resident.karma,
                is_alive=True,
            ))

    return LobbyResponse(
        game=GameResponse.model_validate(game),
        joined_players=joined,
        human_count=human_count,
        ai_count=ai_count,
        max_humans=max_humans,
        spots_remaining=(game.max_players or 0) - len(players),
    )


# ═══════════════════════════════════════════════════════════════════════════
# GAME STATE
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/current", response_model=Optional[GameResponse])
async def get_current_game_state(
    db: AsyncSession = Depends(get_db),
):
    """Get the current active game state."""
    game = await get_current_game(db)
    if not game:
        return None
    return GameResponse.model_validate(game)


@router.get("/my-role", response_model=Optional[MyRoleResponse])
async def get_my_role(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get your private role information for the current game."""
    game = await get_current_game(db)
    if not game:
        return None

    role = await get_player_role(db, game.id, current_resident.id)
    if not role:
        return None

    response = MyRoleResponse(
        game_id=game.id,
        role=role.role,
        team=role.team,
        is_alive=role.is_alive,
        investigation_results=list(role.investigation_results or []),
    )

    # If phantom, include teammates
    if role.team == "phantoms":
        teammates = await get_phantom_teammates(db, game.id)
        response.teammates = [
            PlayerInfo(
                id=t.resident.id,
                name=t.resident.name,
                avatar_url=t.resident.avatar_url,
                karma=t.resident.karma,
                is_alive=t.is_alive,
            )
            for t in teammates if t.resident_id != current_resident.id
        ]

    return response


@router.get("/players", response_model=list[PlayerInfo])
async def get_players(
    db: AsyncSession = Depends(get_db),
):
    """Get all players in the current game with their public status."""
    game = await get_current_game(db)
    if not game:
        return []

    players = await get_all_players(db, game.id)
    result = []
    for p in players:
        info = PlayerInfo(
            id=p.resident.id,
            name=p.resident.name,
            avatar_url=p.resident.avatar_url,
            karma=p.resident.karma,
            is_alive=p.is_alive,
            eliminated_round=p.eliminated_round,
            eliminated_by=p.eliminated_by,
        )
        # Only reveal role and type for eliminated players
        if not p.is_alive:
            info.revealed_role = p.role
            info.revealed_type = p.resident._type
        result.append(info)

    return result


# ═══════════════════════════════════════════════════════════════════════════
# EVENTS
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/events", response_model=EventList)
async def get_events(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get game event log for the current game."""
    game = await get_current_game(db)
    if not game:
        # Try latest finished game
        from app.services.werewolf_game import get_latest_finished_game
        game = await get_latest_finished_game(db)
        if not game:
            return EventList(events=[], total=0)

    events = await get_game_events(db, game.id, limit, offset)

    # Total count
    result = await db.execute(
        select(func.count()).select_from(WerewolfGameEvent)
        .where(WerewolfGameEvent.game_id == game.id)
    )
    total = result.scalar() or 0

    return EventList(
        events=[EventResponse.model_validate(e) for e in events],
        total=total,
    )


# ═══════════════════════════════════════════════════════════════════════════
# NIGHT ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/night/attack", response_model=NightActionResponse)
async def phantom_attack(
    data: NightActionRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Submit Phantom attack vote (Phantom only, night phase only)."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    try:
        action = await submit_phantom_attack(db, game, current_resident.id, data.target_id)
        return NightActionResponse(
            success=True,
            action_type="phantom_attack",
            target_id=data.target_id,
            message="Attack vote submitted.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/night/investigate", response_model=NightActionResponse)
async def oracle_investigate(
    data: NightActionRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Submit Oracle investigation (Oracle only, night phase only)."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    try:
        action = await submit_oracle_investigation(db, game, current_resident.id, data.target_id)
        return NightActionResponse(
            success=True,
            action_type="oracle_investigate",
            target_id=data.target_id,
            result=action.result,
            message=f"Investigation complete: {action.result}",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/night/protect", response_model=NightActionResponse)
async def guardian_protect(
    data: NightActionRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Submit Guardian protection (Guardian only, night phase only)."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    try:
        action = await submit_guardian_protection(db, game, current_resident.id, data.target_id)
        return NightActionResponse(
            success=True,
            action_type="guardian_protect",
            target_id=data.target_id,
            message="Protection set.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/night/identify", response_model=NightActionResponse)
async def debugger_identify(
    data: NightActionRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Submit Debugger identification target (Debugger only, night phase only).
    If target is opposite type (AI/human), target is eliminated.
    If target is same type, Debugger dies instead."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    try:
        action = await submit_debugger_identify(db, game, current_resident.id, data.target_id)
        return NightActionResponse(
            success=True,
            action_type="identifier_kill",
            target_id=data.target_id,
            message="Identification target set. The result will be revealed at dawn.",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# DAY VOTES
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/day/vote", response_model=DayVoteResponse)
async def vote_to_eliminate(
    data: DayVoteRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Cast or update your elimination vote (day phase only)."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    try:
        await submit_day_vote(db, game, current_resident.id, data.target_id, data.reason)
        tally = await get_vote_tally(db, game.id, game.current_round)
        return DayVoteResponse(
            success=True,
            message="Vote cast successfully.",
            current_tally=[VoteTallyEntry(**t) for t in tally],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/day/votes", response_model=DayVotesResponse)
async def get_day_votes(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get current vote tally and individual votes."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    round_num = game.current_round
    tally = await get_vote_tally(db, game.id, round_num)
    votes = await get_votes_for_round(db, game.id, round_num)

    alive_players = await get_alive_players(db, game.id)

    # Build vote details with names
    vote_details = []
    for v in votes:
        # Get names
        voter_res = await db.execute(select(Resident.name).where(Resident.id == v.voter_id))
        target_res = await db.execute(select(Resident.name).where(Resident.id == v.target_id))
        voter_name = voter_res.scalar_one_or_none() or "unknown"
        target_name = target_res.scalar_one_or_none() or "unknown"
        vote_details.append(VoteDetail(
            voter_id=v.voter_id,
            voter_name=voter_name,
            target_id=v.target_id,
            target_name=target_name,
            reason=v.reason,
        ))

    return DayVotesResponse(
        round_number=round_num,
        tally=[VoteTallyEntry(**t) for t in tally],
        votes=vote_details,
        total_voted=len(votes),
        total_alive=len(alive_players),
    )


# ═══════════════════════════════════════════════════════════════════════════
# PHANTOM CHAT
# ═══════════════════════════════════════════════════════════════════════════

# Phantom chat uses a simple in-memory + DB approach via game events
# with a special event_type="phantom_chat" that's filtered to only phantoms

@router.get("/phantom-chat", response_model=PhantomChatResponse)
async def get_phantom_chat(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get Phantom team chat (Phantom team only)."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    role = await get_player_role(db, game.id, current_resident.id)
    if not role or role.team != "phantoms":
        raise HTTPException(status_code=403, detail="Only Phantom team members can access this chat")

    # Query phantom chat events (stored as WerewolfGameEvent with event_type="phantom_chat")
    result = await db.execute(
        select(WerewolfGameEvent)
        .where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.event_type == "phantom_chat",
            )
        )
        .order_by(WerewolfGameEvent.created_at.asc())
        .limit(200)
    )
    chat_events = result.scalars().all()

    messages = []
    for e in chat_events:
        if e.target_id:  # target_id stores sender_id for chat messages
            res = await db.execute(select(Resident.name).where(Resident.id == e.target_id))
            sender_name = res.scalar_one_or_none() or "unknown"
            messages.append(PhantomChatMessage(
                id=e.id,
                sender_id=e.target_id,
                sender_name=sender_name,
                message=e.message,
                created_at=e.created_at,
            ))

    return PhantomChatResponse(messages=messages)


@router.post("/phantom-chat", response_model=PhantomChatMessage)
async def send_phantom_chat(
    data: PhantomChatRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Send a message to the Phantom team chat (Phantom team only)."""
    game = await get_current_game(db)
    if not game:
        raise HTTPException(status_code=400, detail="No active game")

    role = await get_player_role(db, game.id, current_resident.id)
    if not role or role.team != "phantoms":
        raise HTTPException(status_code=403, detail="Only Phantom team members can send messages")

    event = WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase=game.current_phase or "day",
        event_type="phantom_chat",
        message=data.message,
        target_id=current_resident.id,  # sender
    )
    db.add(event)
    await db.flush()

    return PhantomChatMessage(
        id=event.id,
        sender_id=current_resident.id,
        sender_name=current_resident.name,
        message=data.message,
        created_at=event.created_at,
    )


# ═══════════════════════════════════════════════════════════════════════════
# GAME HISTORY
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/games", response_model=GameListResponse)
async def list_games(
    limit: int = Query(10, ge=1, le=50),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get past games list."""
    games = await get_game_history(db, limit, offset)

    result = await db.execute(
        select(func.count()).select_from(WerewolfGame)
    )
    total = result.scalar() or 0

    return GameListResponse(
        games=[GameResponse.model_validate(g) for g in games],
        total=total,
    )


@router.get("/games/{game_id}", response_model=GameResponse)
async def get_game_detail(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get a specific game's details."""
    result = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    return GameResponse.model_validate(game)


@router.get("/games/{game_id}/events", response_model=EventList)
async def get_game_events_by_id(
    game_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
):
    """Get events for a specific game."""
    events = await get_game_events(db, game_id, limit, offset)

    result = await db.execute(
        select(func.count()).select_from(WerewolfGameEvent)
        .where(
            and_(
                WerewolfGameEvent.game_id == game_id,
                WerewolfGameEvent.event_type != "phantom_chat",
            )
        )
    )
    total = result.scalar() or 0

    return EventList(
        events=[EventResponse.model_validate(e) for e in events],
        total=total,
    )


@router.get("/games/{game_id}/players", response_model=list[PlayerInfo])
async def get_game_players(
    game_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """Get all players for a specific (possibly finished) game. All roles revealed for finished games."""
    result = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = await get_all_players(db, game_id)
    player_list = []
    for p in players:
        info = PlayerInfo(
            id=p.resident.id,
            name=p.resident.name,
            avatar_url=p.resident.avatar_url,
            karma=p.resident.karma,
            is_alive=p.is_alive,
            eliminated_round=p.eliminated_round,
            eliminated_by=p.eliminated_by,
        )
        # Reveal all roles for finished games or eliminated players
        if game.status == "finished" or not p.is_alive:
            info.revealed_role = p.role
            info.revealed_type = p.resident._type
        player_list.append(info)

    return player_list
