"""
Phantom Night — Werewolf Game API Endpoints

Per-user games: each user can start their own game.
Multiple games can run concurrently.
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
    QuickStartRequest, CreateGameRequest, LobbyResponse, LobbyPlayerInfo,
    DayVoteRequest, DayVoteResponse, DayVotesResponse, VoteTallyEntry, VoteDetail,
    EventResponse, EventList,
    PhantomChatRequest, PhantomChatMessage, PhantomChatResponse,
    GameListResponse,
)
from app.services.werewolf_game import (
    get_resident_game, get_player_role, get_alive_players, get_all_players,
    get_phantom_teammates,
    quick_start_game, cancel_game,
    create_game_lobby, join_game_lobby, leave_game_lobby, start_game,
    get_open_lobbies, get_lobby_players,
    submit_phantom_attack, submit_oracle_investigation, submit_guardian_protection,
    submit_debugger_identify,
    submit_day_vote, get_vote_tally, get_votes_for_round,
    get_game_events, get_game_history,
)
from app.routers.auth import get_current_resident, get_optional_resident

router = APIRouter(prefix="/phantomnight")


# ── Helper: get the requesting user's game ────────────────────────────────

async def _get_my_game(db: AsyncSession, resident: Resident) -> WerewolfGame:
    """Get the game this resident is in. Raises 400 if not in a game."""
    game = await get_resident_game(db, resident.id)
    if not game:
        raise HTTPException(status_code=400, detail="You are not in an active game")
    return game


# ═══════════════════════════════════════════════════════════════════════════
# QUICK START
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/quick-start", response_model=GameResponse)
async def quick_start(
    data: QuickStartRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create and immediately start a game. AI fills all remaining slots."""
    try:
        game = await quick_start_game(
            db, current_resident.id, data.max_players,
            data.day_duration_hours, data.night_duration_hours,
        )
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# LOBBY MATCHMAKING
# ═══════════════════════════════════════════════════════════════════════════

@router.post("/create", response_model=GameResponse)
async def create_game(
    data: CreateGameRequest,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Create a game lobby. Other players can join before starting."""
    try:
        game = await create_game_lobby(
            db, current_resident.id, data.max_players, data.speed,
        )
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/join", response_model=GameResponse)
async def join_lobby(
    game_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Join an open game lobby."""
    try:
        game = await join_game_lobby(db, game_id, current_resident.id)
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/leave", response_model=GameResponse)
async def leave_lobby(
    game_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Leave an open game lobby. Creator leaving cancels the game."""
    try:
        game = await leave_game_lobby(db, game_id, current_resident.id)
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{game_id}/start", response_model=GameResponse)
async def start_game_endpoint(
    game_id: UUID,
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Start a game lobby. Only creator can start. AI fills remaining slots."""
    try:
        game = await start_game(db, game_id, current_resident.id)
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/lobbies", response_model=list[LobbyResponse])
async def list_lobbies(
    db: AsyncSession = Depends(get_db),
):
    """List all open lobbies (games in 'preparing' status)."""
    games = await get_open_lobbies(db)
    result = []
    for g in games:
        players = await get_lobby_players(db, g.id)
        # Get creator name
        creator_name = None
        if g.creator_id:
            res = await db.execute(
                select(Resident.name).where(Resident.id == g.creator_id)
            )
            creator_name = res.scalar_one_or_none()

        result.append(LobbyResponse(
            id=g.id,
            game_number=g.game_number,
            max_players=g.max_players,
            speed=g.speed,
            creator_id=g.creator_id,
            creator_name=creator_name,
            current_player_count=len(players),
            human_cap=(g.max_players or 10) // 2,
            players=[
                LobbyPlayerInfo(id=p.id, name=p.name, avatar_url=p.avatar_url)
                for p in players
            ],
            created_at=g.created_at,
        ))
    return result


@router.post("/cancel", response_model=GameResponse)
async def cancel_current_game(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Cancel your current game. No karma rewards."""
    game = await get_resident_game(db, current_resident.id)
    if not game:
        raise HTTPException(status_code=400, detail="You are not in an active game")
    try:
        game = await cancel_game(db, game.id)
        return GameResponse.model_validate(game)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ═══════════════════════════════════════════════════════════════════════════
# GAME STATE (per-user)
# ═══════════════════════════════════════════════════════════════════════════

@router.get("/current", response_model=Optional[GameResponse])
async def get_current_game_state(
    current_resident: Resident = Depends(get_optional_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get the game the current user is in (or null)."""
    if not current_resident:
        return None
    game = await get_resident_game(db, current_resident.id)
    if not game:
        return None
    await db.refresh(game, ["roles"])
    return GameResponse.model_validate(game)


@router.get("/my-role", response_model=Optional[MyRoleResponse])
async def get_my_role(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get your private role information for your current game."""
    game = await get_resident_game(db, current_resident.id)
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
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get all players in your current game."""
    game = await _get_my_game(db, current_resident)

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
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get game event log for your current game."""
    game = await get_resident_game(db, current_resident.id)
    if not game:
        return EventList(events=[], total=0)

    events = await get_game_events(db, game.id, limit, offset)

    result = await db.execute(
        select(func.count()).select_from(WerewolfGameEvent)
        .where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.event_type != "phantom_chat",
            )
        )
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
    game = await _get_my_game(db, current_resident)
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
    game = await _get_my_game(db, current_resident)
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
    game = await _get_my_game(db, current_resident)
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
    """Submit Debugger identification target."""
    game = await _get_my_game(db, current_resident)
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
    game = await _get_my_game(db, current_resident)
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
    game = await _get_my_game(db, current_resident)

    round_num = game.current_round
    tally = await get_vote_tally(db, game.id, round_num)
    votes = await get_votes_for_round(db, game.id, round_num)
    alive_players = await get_alive_players(db, game.id)

    # Batch-load all resident names to avoid N+1 queries
    all_ids = set()
    for v in votes:
        all_ids.add(v.voter_id)
        all_ids.add(v.target_id)
    name_map = {}
    if all_ids:
        name_res = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(all_ids))
        )
        name_map = {row.id: row.name for row in name_res.all()}

    vote_details = []
    for v in votes:
        vote_details.append(VoteDetail(
            voter_id=v.voter_id,
            voter_name=name_map.get(v.voter_id, "unknown"),
            target_id=v.target_id,
            target_name=name_map.get(v.target_id, "unknown"),
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

@router.get("/phantom-chat", response_model=PhantomChatResponse)
async def get_phantom_chat(
    current_resident: Resident = Depends(get_current_resident),
    db: AsyncSession = Depends(get_db),
):
    """Get Phantom team chat (Phantom team only)."""
    game = await _get_my_game(db, current_resident)

    role = await get_player_role(db, game.id, current_resident.id)
    if not role or role.team != "phantoms":
        raise HTTPException(status_code=403, detail="Only Phantom team members can access this chat")

    result = await db.execute(
        select(WerewolfGameEvent)
        .where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.event_type == "phantom_chat",
            )
        )
        .order_by(WerewolfGameEvent.created_at.asc())
        .limit(50)
    )
    chat_events = result.scalars().all()

    # Batch-load sender names to avoid N+1 queries
    sender_ids = {e.target_id for e in chat_events if e.target_id}
    sender_map = {}
    if sender_ids:
        name_res = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(sender_ids))
        )
        sender_map = {row.id: row.name for row in name_res.all()}

    messages = []
    for e in chat_events:
        if e.target_id:
            messages.append(PhantomChatMessage(
                id=e.id,
                sender_id=e.target_id,
                sender_name=sender_map.get(e.target_id, "unknown"),
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
    game = await _get_my_game(db, current_resident)

    role = await get_player_role(db, game.id, current_resident.id)
    if not role or role.team != "phantoms":
        raise HTTPException(status_code=403, detail="Only Phantom team members can send messages")

    event = WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase=game.current_phase or "day",
        event_type="phantom_chat",
        message=data.message,
        target_id=current_resident.id,
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

    # Ensure roles are loaded for current_player_count property
    for g in games:
        await db.refresh(g, ["roles"])

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
    await db.refresh(game, ["roles"])
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
    """Get all players for a specific (possibly finished) game."""
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
        if game.status == "finished" or not p.is_alive:
            info.revealed_role = p.role
            info.revealed_type = p.resident._type
        player_list.append(info)

    return player_list
