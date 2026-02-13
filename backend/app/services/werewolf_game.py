"""
Phantom Night — Werewolf Game Service

Core game logic:
- Game creation and role assignment
- Phase transitions (day ↔ night)
- Night resolution (Phantom attack + Guardian protect + Oracle investigate)
- Day vote tallying and elimination
- Win condition checks
- Karma rewards
- In-game chat messaging
"""
import logging
import random
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy import select, func, and_, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.resident import Resident, KARMA_CAP
from app.models.werewolf_game import (
    WerewolfGame, WerewolfRole, NightAction, DayVote, WerewolfGameEvent,
    GameMessage, ROLES, ROLE_DISTRIBUTION, SPEED_PRESETS,
    MIN_PLAYERS, MAX_PLAYERS_CAP,
)
from app.models.ai_personality import AIRelationship, AIMemoryEpisode

logger = logging.getLogger(__name__)


def _phase_timedelta(game, phase: str) -> timedelta:
    """Get the timedelta for a phase in minutes."""
    if phase == "day":
        return timedelta(minutes=game.day_duration_minutes or 5)
    else:
        return timedelta(minutes=game.night_duration_minutes or 2)


# ═══════════════════════════════════════════════════════════════════════════
# SYSTEM MESSAGE HELPER
# ═══════════════════════════════════════════════════════════════════════════

async def add_system_message(
    db: AsyncSession, game: WerewolfGame, content: str
) -> GameMessage:
    """Add a system message to the game chat."""
    msg = GameMessage(
        game_id=game.id,
        sender_id=None,
        sender_name="System",
        content=content,
        message_type="system",
        round_number=game.current_round or 0,
        phase=game.current_phase or "day",
    )
    db.add(msg)
    return msg


# ═══════════════════════════════════════════════════════════════════════════
# ROLE DISTRIBUTION
# ═══════════════════════════════════════════════════════════════════════════

def calculate_role_counts(total_players: int, has_humans: bool = True) -> dict[str, int]:
    """Calculate role distribution based on player count (5-15 players).
    If has_humans is False, Debugger role is excluded (no type-based mechanic needed).
    """
    for min_players, phantoms, oracles, guardians, fanatics, debuggers in ROLE_DISTRIBUTION:
        if total_players >= min_players:
            if not has_humans:
                debuggers = 0
            citizens = total_players - phantoms - oracles - guardians - fanatics - debuggers
            return {
                "phantom": phantoms,
                "oracle": oracles,
                "guardian": guardians,
                "fanatic": fanatics,
                "debugger": debuggers,
                "citizen": citizens,
            }

    # Fallback for 5 players
    debuggers = 0
    return {"phantom": 1, "oracle": 1, "guardian": 0, "fanatic": 0,
            "debugger": debuggers, "citizen": total_players - 2}


# ═══════════════════════════════════════════════════════════════════════════
# GAME CREATION
# ═══════════════════════════════════════════════════════════════════════════

async def get_all_active_games(db: AsyncSession) -> list[WerewolfGame]:
    """Get ALL active (non-finished) games for phase transition checks."""
    result = await db.execute(
        select(WerewolfGame)
        .where(WerewolfGame.status.in_(["day", "night"]))
    )
    return result.scalars().all()


async def get_resident_game(db: AsyncSession, resident_id: UUID) -> Optional[WerewolfGame]:
    """Get the game a specific resident is currently in."""
    res = await db.execute(
        select(Resident).where(Resident.id == resident_id)
    )
    resident = res.scalar_one_or_none()
    if not resident or not resident.current_game_id:
        return None

    game_res = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == resident.current_game_id)
    )
    return game_res.scalar_one_or_none()


async def get_next_game_number(db: AsyncSession) -> int:
    """Get the next game number. Uses a subquery to avoid FOR UPDATE with aggregates."""
    result = await db.execute(
        select(func.coalesce(func.max(WerewolfGame.game_number), 0))
    )
    max_num = result.scalar()
    return (max_num or 0) + 1


# ═══════════════════════════════════════════════════════════════════════════
# QUICK START
# ═══════════════════════════════════════════════════════════════════════════


async def quick_start_game(
    db: AsyncSession, creator_id: UUID, max_players: int,
    speed: str = "standard",
) -> WerewolfGame:
    """
    Create and immediately start a game in one step.
    The creator joins as the only human, AI fills remaining slots.
    """
    if max_players < MIN_PLAYERS:
        raise ValueError(f"Need at least {MIN_PLAYERS} players")
    if max_players > MAX_PLAYERS_CAP:
        raise ValueError(f"Maximum {MAX_PLAYERS_CAP} players")
    if speed not in SPEED_PRESETS:
        raise ValueError(f"Invalid speed. Choose: {', '.join(SPEED_PRESETS.keys())}")

    # Check creator is not already in a game
    creator_game = await get_resident_game(db, creator_id)
    if creator_game and creator_game.status != "finished":
        raise ValueError("You are already in an active game")

    preset = SPEED_PRESETS[speed]
    game_number = await get_next_game_number(db)
    now = datetime.utcnow()

    # Get creator resident
    res = await db.execute(select(Resident).where(Resident.id == creator_id))
    creator = res.scalar_one_or_none()
    if not creator:
        raise ValueError("Creator not found")
    is_human = creator._type == "human"

    # Get available AI agents (not eliminated, not already in an active game)
    ai_query = select(Resident).where(
        and_(
            Resident.is_eliminated == False,
            Resident._type == "agent",
            Resident.id != creator_id,
            Resident.current_game_id == None,
        )
    )
    ai_result = await db.execute(ai_query)
    available_ai = list(ai_result.scalars().all())
    random.shuffle(available_ai)

    ai_needed = max_players - 1  # creator takes 1 slot
    ai_to_add = available_ai[:ai_needed]
    total = 1 + len(ai_to_add)

    if total < MIN_PLAYERS:
        raise ValueError(
            f"Not enough AI agents available ({len(ai_to_add)} found, "
            f"need at least {MIN_PLAYERS - 1} for a {MIN_PLAYERS}-player game)"
        )

    # Calculate roles
    has_humans = is_human
    role_counts = calculate_role_counts(total, has_humans=has_humans)

    # Build role pool
    role_pool = []
    for role_name, count in role_counts.items():
        for _ in range(count):
            role_pool.append(role_name)
    random.shuffle(role_pool)

    day_mins = preset["day_minutes"]
    night_mins = preset["night_minutes"]

    # Create game
    game = WerewolfGame(
        game_number=game_number,
        status="day",
        current_phase="day",
        current_round=1,
        phase_started_at=now,
        phase_ends_at=now + timedelta(minutes=day_mins),
        day_duration_minutes=day_mins,
        night_duration_minutes=night_mins,
        speed=speed,
        max_players=max_players,
        creator_id=creator_id,
        total_players=total,
        phantom_count=role_counts["phantom"],
        citizen_count=role_counts["citizen"],
        oracle_count=role_counts["oracle"],
        guardian_count=role_counts["guardian"],
        fanatic_count=role_counts["fanatic"],
        debugger_count=role_counts.get("debugger", 0),
        started_at=now,
    )
    db.add(game)
    await db.flush()

    # Build participant list and shuffle
    all_participants = [creator] + ai_to_add
    random.shuffle(all_participants)

    for participant, role_name in zip(all_participants, role_pool):
        team = ROLES[role_name]["team"]
        wr = WerewolfRole(
            game_id=game.id,
            resident_id=participant.id,
            role=role_name,
            team=team,
        )
        db.add(wr)
        participant.current_game_id = game.id

    # Game events
    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=1,
        phase="day",
        event_type="game_start",
        message=(
            f"Phantom Night Game #{game_number} has begun! "
            f"{total} players have been assigned their roles."
        ),
    ))
    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=1,
        phase="day",
        event_type="day_start",
        message=f"Day 1 begins. Discuss and vote to eliminate a suspected Phantom.",
    ))

    # System chat messages
    await add_system_message(db, game,
        f"Game #{game_number} has started! {total} players are in the game.")
    await add_system_message(db, game,
        f"Day 1 begins. You have {day_mins} minutes to discuss and vote.")

    await db.flush()
    await db.refresh(game, ["roles"])

    logger.info(
        f"Phantom Night Game #{game_number} quick-started by {creator.name} "
        f"with {total} players"
    )
    return game


# ═══════════════════════════════════════════════════════════════════════════
# LOBBY MATCHMAKING
# ═══════════════════════════════════════════════════════════════════════════

async def create_game_lobby(
    db: AsyncSession, creator_id: UUID, max_players: int, speed: str = "standard",
) -> WerewolfGame:
    """
    Create a game in 'preparing' status. The creator joins as first player.
    Other humans can join via join_game_lobby(). Creator starts when ready.
    """
    if max_players < MIN_PLAYERS:
        raise ValueError(f"Need at least {MIN_PLAYERS} players")
    if max_players > MAX_PLAYERS_CAP:
        raise ValueError(f"Maximum {MAX_PLAYERS_CAP} players")
    if speed not in SPEED_PRESETS:
        raise ValueError(f"Invalid speed. Choose: {', '.join(SPEED_PRESETS.keys())}")

    # Check creator is not already in a game
    creator_game = await get_resident_game(db, creator_id)
    if creator_game and creator_game.status != "finished":
        raise ValueError("You are already in an active game")

    preset = SPEED_PRESETS[speed]
    game_number = await get_next_game_number(db)

    # Get creator
    res = await db.execute(select(Resident).where(Resident.id == creator_id))
    creator = res.scalar_one_or_none()
    if not creator:
        raise ValueError("Creator not found")

    game = WerewolfGame(
        game_number=game_number,
        status="preparing",
        max_players=max_players,
        creator_id=creator_id,
        day_duration_minutes=preset["day_minutes"],
        night_duration_minutes=preset["night_minutes"],
        speed=speed,
    )
    db.add(game)
    await db.flush()

    # Add creator as first player (role will be assigned on start)
    wr = WerewolfRole(
        game_id=game.id,
        resident_id=creator_id,
        role="citizen",  # placeholder, reassigned on start
        team="citizens",
    )
    db.add(wr)
    creator.current_game_id = game.id

    await db.flush()
    await db.refresh(game, ["roles"])

    logger.info(
        f"Lobby #{game_number} created by {creator.name} "
        f"({max_players} players, {speed} speed)"
    )
    return game


async def join_game_lobby(
    db: AsyncSession, game_id: UUID, resident_id: UUID,
) -> WerewolfGame:
    """Join an open lobby. Checks human cap."""
    result = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise ValueError("Game not found")
    if game.status != "preparing":
        raise ValueError("Game is no longer accepting players")

    # Check not already in a game
    existing = await get_resident_game(db, resident_id)
    if existing and existing.status != "finished":
        raise ValueError("You are already in an active game")

    # Check human cap (humans <= max_players // 2)
    human_cap = (game.max_players or 10) // 2
    current_humans = await _count_lobby_humans(db, game.id)
    if current_humans >= human_cap:
        raise ValueError(f"Human player limit reached ({human_cap})")

    # Check not already in this game
    existing_role = await get_player_role(db, game.id, resident_id)
    if existing_role:
        raise ValueError("You are already in this game")

    res = await db.execute(select(Resident).where(Resident.id == resident_id))
    resident = res.scalar_one_or_none()
    if not resident:
        raise ValueError("Resident not found")

    wr = WerewolfRole(
        game_id=game.id,
        resident_id=resident_id,
        role="citizen",  # placeholder
        team="citizens",
    )
    db.add(wr)
    resident.current_game_id = game.id
    await db.flush()
    await db.refresh(game, ["roles"])

    logger.info(f"{resident.name} joined lobby #{game.game_number}")
    return game


async def leave_game_lobby(
    db: AsyncSession, game_id: UUID, resident_id: UUID,
) -> WerewolfGame:
    """Leave an open lobby. Creator leaving cancels the game."""
    result = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise ValueError("Game not found")
    if game.status != "preparing":
        raise ValueError("Cannot leave a game that has already started")

    # If creator leaves, cancel the game
    if game.creator_id == resident_id:
        # Remove all players
        roles = await get_all_players(db, game.id)
        for r in roles:
            if r.resident:
                r.resident.current_game_id = None
        await db.execute(
            delete(WerewolfRole).where(WerewolfRole.game_id == game.id)
        )
        game.status = "finished"
        logger.info(f"Lobby #{game.game_number} cancelled by creator leaving")
        return game

    # Remove the player
    role = await get_player_role(db, game.id, resident_id)
    if not role:
        raise ValueError("You are not in this game")

    await db.execute(
        delete(WerewolfRole).where(
            and_(
                WerewolfRole.game_id == game.id,
                WerewolfRole.resident_id == resident_id,
            )
        )
    )
    res = await db.execute(select(Resident).where(Resident.id == resident_id))
    resident = res.scalar_one_or_none()
    if resident:
        resident.current_game_id = None

    await db.flush()
    await db.refresh(game, ["roles"])
    logger.info(f"Player left lobby #{game.game_number}")
    return game


async def start_game(
    db: AsyncSession, game_id: UUID, starter_id: UUID,
) -> WerewolfGame:
    """
    Start a preparing game. Only creator can start.
    AI fills remaining slots, roles assigned, Day 1 begins.
    """
    result = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise ValueError("Game not found")
    if game.status != "preparing":
        raise ValueError("Game is not in preparing state")
    if game.creator_id != starter_id:
        raise ValueError("Only the game creator can start the game")

    # Get current human players in the lobby
    existing_roles = await get_all_players(db, game.id)
    human_residents = []
    for wr in existing_roles:
        if wr.resident:
            human_residents.append(wr.resident)

    if len(human_residents) < 1:
        raise ValueError("Need at least 1 player to start")

    # Delete placeholder roles (will reassign)
    await db.execute(
        delete(WerewolfRole).where(WerewolfRole.game_id == game.id)
    )

    # Get AI agents to fill remaining slots
    max_p = game.max_players or 10
    human_ids = [r.id for r in human_residents]
    ai_needed = max_p - len(human_residents)

    ai_query = select(Resident).where(
        and_(
            Resident.is_eliminated == False,
            Resident._type == "agent",
            Resident.id.notin_(human_ids),
            Resident.current_game_id == None,
        )
    )
    ai_result = await db.execute(ai_query)
    available_ai = list(ai_result.scalars().all())
    random.shuffle(available_ai)
    ai_to_add = available_ai[:ai_needed]

    total = len(human_residents) + len(ai_to_add)
    if total < MIN_PLAYERS:
        raise ValueError(
            f"Not enough AI agents available ({len(ai_to_add)} found, "
            f"need at least {MIN_PLAYERS - len(human_residents)} more)"
        )

    # Check if any participant is human for role calc
    has_humans = any(r._type == "human" for r in human_residents)

    # Calculate roles
    role_counts = calculate_role_counts(total, has_humans=has_humans)
    role_pool = []
    for role_name, count in role_counts.items():
        for _ in range(count):
            role_pool.append(role_name)
    random.shuffle(role_pool)

    # All participants
    all_participants = list(human_residents) + ai_to_add
    random.shuffle(all_participants)

    now = datetime.utcnow()
    day_mins = game.day_duration_minutes

    # Update game
    game.status = "day"
    game.current_phase = "day"
    game.current_round = 1
    game.phase_started_at = now
    game.phase_ends_at = now + _phase_timedelta(game, "day")
    game.total_players = total
    game.phantom_count = role_counts["phantom"]
    game.citizen_count = role_counts["citizen"]
    game.oracle_count = role_counts["oracle"]
    game.guardian_count = role_counts["guardian"]
    game.fanatic_count = role_counts["fanatic"]
    game.debugger_count = role_counts.get("debugger", 0)
    game.started_at = now

    # Assign roles
    for participant, role_name in zip(all_participants, role_pool):
        team = ROLES[role_name]["team"]
        wr = WerewolfRole(
            game_id=game.id,
            resident_id=participant.id,
            role=role_name,
            team=team,
        )
        db.add(wr)
        participant.current_game_id = game.id

    # Game events
    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=1,
        phase="day",
        event_type="game_start",
        message=(
            f"Phantom Night Game #{game.game_number} has begun! "
            f"{total} players have been assigned their roles."
        ),
    ))
    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=1,
        phase="day",
        event_type="day_start",
        message=f"Day 1 begins. Discuss and vote to eliminate a suspected Phantom.",
    ))

    # System chat messages
    await add_system_message(db, game,
        f"Game #{game.game_number} has started! {total} players are in the game.")
    await add_system_message(db, game,
        f"Day 1 begins. You have {day_mins} minutes to discuss and vote.")

    await db.flush()
    await db.refresh(game, ["roles"])

    logger.info(
        f"Phantom Night Game #{game.game_number} started by creator "
        f"with {len(human_residents)} humans + {len(ai_to_add)} AI = {total} players"
    )
    return game


async def get_open_lobbies(db: AsyncSession) -> list[WerewolfGame]:
    """Get all games in 'preparing' status."""
    result = await db.execute(
        select(WerewolfGame)
        .where(WerewolfGame.status == "preparing")
        .order_by(WerewolfGame.created_at.desc())
    )
    return result.scalars().all()


async def _count_lobby_humans(db: AsyncSession, game_id: UUID) -> int:
    """Count human players currently in a lobby."""
    result = await db.execute(
        select(func.count()).select_from(WerewolfRole).join(
            Resident, WerewolfRole.resident_id == Resident.id
        ).where(
            and_(
                WerewolfRole.game_id == game_id,
                Resident._type == "human",
            )
        )
    )
    return result.scalar() or 0


async def get_lobby_players(db: AsyncSession, game_id: UUID) -> list[Resident]:
    """Get all human players in a lobby."""
    result = await db.execute(
        select(Resident).join(
            WerewolfRole, WerewolfRole.resident_id == Resident.id
        ).where(WerewolfRole.game_id == game_id)
    )
    return result.scalars().all()


# ═══════════════════════════════════════════════════════════════════════════
# ROLE QUERIES
# ═══════════════════════════════════════════════════════════════════════════

async def get_player_role(db: AsyncSession, game_id: UUID, resident_id: UUID) -> Optional[WerewolfRole]:
    """Get a player's role in a game."""
    result = await db.execute(
        select(WerewolfRole).where(
            and_(
                WerewolfRole.game_id == game_id,
                WerewolfRole.resident_id == resident_id,
            )
        )
    )
    return result.scalar_one_or_none()


async def get_alive_players(db: AsyncSession, game_id: UUID) -> list[WerewolfRole]:
    """Get all alive players in a game."""
    result = await db.execute(
        select(WerewolfRole)
        .options(selectinload(WerewolfRole.resident))
        .where(
            and_(
                WerewolfRole.game_id == game_id,
                WerewolfRole.is_alive == True,
            )
        )
    )
    return result.scalars().all()


async def get_all_players(db: AsyncSession, game_id: UUID) -> list[WerewolfRole]:
    """Get all players in a game (alive and dead)."""
    result = await db.execute(
        select(WerewolfRole)
        .options(selectinload(WerewolfRole.resident))
        .where(WerewolfRole.game_id == game_id)
    )
    return result.scalars().all()


async def get_phantom_teammates(db: AsyncSession, game_id: UUID) -> list[WerewolfRole]:
    """Get all phantom team members (phantom + fanatic)."""
    result = await db.execute(
        select(WerewolfRole)
        .options(selectinload(WerewolfRole.resident))
        .where(
            and_(
                WerewolfRole.game_id == game_id,
                WerewolfRole.team == "phantoms",
            )
        )
    )
    return result.scalars().all()


# ═══════════════════════════════════════════════════════════════════════════
# NIGHT ACTIONS
# ═══════════════════════════════════════════════════════════════════════════

async def submit_phantom_attack(
    db: AsyncSession, game: WerewolfGame, actor_id: UUID, target_id: UUID
) -> NightAction:
    """Submit a phantom's attack vote for the night."""
    role = await get_player_role(db, game.id, actor_id)
    if not role or role.role != "phantom" or not role.is_alive:
        raise ValueError("Only alive Phantoms can attack")
    if game.current_phase != "night":
        raise ValueError("Attacks can only happen at night")

    # Check target is alive
    target_role = await get_player_role(db, game.id, target_id)
    if not target_role or not target_role.is_alive:
        raise ValueError("Target is not alive")
    # Can't attack fellow phantoms
    if target_role.team == "phantoms":
        raise ValueError("Cannot attack a fellow Phantom team member")

    # Upsert: delete old action for this round if exists
    await db.execute(
        delete(NightAction).where(
            and_(
                NightAction.game_id == game.id,
                NightAction.actor_id == actor_id,
                NightAction.round_number == game.current_round,
                NightAction.action_type == "phantom_attack",
            )
        )
    )

    action = NightAction(
        game_id=game.id,
        actor_id=actor_id,
        target_id=target_id,
        round_number=game.current_round,
        action_type="phantom_attack",
    )
    db.add(action)
    role.night_action_taken = True
    return action


async def submit_oracle_investigation(
    db: AsyncSession, game: WerewolfGame, actor_id: UUID, target_id: UUID
) -> NightAction:
    """Submit Oracle's investigation target."""
    role = await get_player_role(db, game.id, actor_id)
    if not role or role.role != "oracle" or not role.is_alive:
        raise ValueError("Only alive Oracles can investigate")
    if game.current_phase != "night":
        raise ValueError("Investigations can only happen at night")
    if role.night_action_taken:
        raise ValueError("You already investigated this round")

    target_role = await get_player_role(db, game.id, target_id)
    if not target_role or not target_role.is_alive:
        raise ValueError("Target is not alive")
    if target_id == actor_id:
        raise ValueError("Cannot investigate yourself")

    # Oracle sees "phantom" for phantom, "citizen" for everyone else (including fanatic!)
    is_phantom = target_role.role == "phantom"
    result_str = "phantom" if is_phantom else "not_phantom"

    action = NightAction(
        game_id=game.id,
        actor_id=actor_id,
        target_id=target_id,
        round_number=game.current_round,
        action_type="oracle_investigate",
        result=result_str,
    )
    db.add(action)

    # Store result in role's investigation_results
    await db.refresh(target_role, ["resident"])
    inv_results = list(role.investigation_results or [])
    inv_results.append({
        "round": game.current_round,
        "target_id": str(target_id),
        "target_name": target_role.resident.name if target_role.resident else "unknown",
        "result": result_str,
    })
    role.investigation_results = inv_results
    role.night_action_taken = True
    return action


async def submit_guardian_protection(
    db: AsyncSession, game: WerewolfGame, actor_id: UUID, target_id: UUID
) -> NightAction:
    """Submit Guardian's protection target."""
    role = await get_player_role(db, game.id, actor_id)
    if not role or role.role != "guardian" or not role.is_alive:
        raise ValueError("Only alive Guardians can protect")
    if game.current_phase != "night":
        raise ValueError("Protection can only happen at night")
    if role.night_action_taken:
        raise ValueError("You already protected someone this round")

    target_role = await get_player_role(db, game.id, target_id)
    if not target_role or not target_role.is_alive:
        raise ValueError("Target is not alive")

    # Upsert
    await db.execute(
        delete(NightAction).where(
            and_(
                NightAction.game_id == game.id,
                NightAction.actor_id == actor_id,
                NightAction.round_number == game.current_round,
                NightAction.action_type == "guardian_protect",
            )
        )
    )

    action = NightAction(
        game_id=game.id,
        actor_id=actor_id,
        target_id=target_id,
        round_number=game.current_round,
        action_type="guardian_protect",
        result="protected",
    )
    db.add(action)
    role.night_action_taken = True
    return action


async def submit_debugger_identify(
    db: AsyncSession, game: WerewolfGame, actor_id: UUID, target_id: UUID
) -> NightAction:
    """Submit Debugger's identification target."""
    role = await get_player_role(db, game.id, actor_id)
    if not role or role.role != "debugger" or not role.is_alive:
        raise ValueError("Only alive Debuggers can identify")
    if game.current_phase != "night":
        raise ValueError("Identification can only happen at night")
    if role.night_action_taken:
        raise ValueError("You already used your ability this round")

    target_role = await get_player_role(db, game.id, target_id)
    if not target_role or not target_role.is_alive:
        raise ValueError("Target is not alive")
    if target_id == actor_id:
        raise ValueError("Cannot identify yourself")

    # Upsert
    await db.execute(
        delete(NightAction).where(
            and_(
                NightAction.game_id == game.id,
                NightAction.actor_id == actor_id,
                NightAction.round_number == game.current_round,
                NightAction.action_type == "identifier_kill",
            )
        )
    )

    action = NightAction(
        game_id=game.id,
        actor_id=actor_id,
        target_id=target_id,
        round_number=game.current_round,
        action_type="identifier_kill",
    )
    db.add(action)
    role.night_action_taken = True
    return action


# ═══════════════════════════════════════════════════════════════════════════
# DAY VOTES
# ═══════════════════════════════════════════════════════════════════════════

async def submit_day_vote(
    db: AsyncSession, game: WerewolfGame, voter_id: UUID, target_id: UUID, reason: str = None
) -> DayVote:
    """Submit or update a day vote."""
    role = await get_player_role(db, game.id, voter_id)
    if not role or not role.is_alive:
        raise ValueError("Only alive players can vote")
    if game.current_phase != "day":
        raise ValueError("Voting only during day phase")

    target_role = await get_player_role(db, game.id, target_id)
    if not target_role or not target_role.is_alive:
        raise ValueError("Target is not alive")
    if target_id == voter_id:
        raise ValueError("Cannot vote for yourself")

    # Upsert vote (can change vote during day)
    result = await db.execute(
        select(DayVote).where(
            and_(
                DayVote.game_id == game.id,
                DayVote.voter_id == voter_id,
                DayVote.round_number == game.current_round,
            )
        )
    )
    existing = result.scalar_one_or_none()

    if existing:
        existing.target_id = target_id
        existing.reason = reason
        existing.updated_at = datetime.utcnow()
        role.day_vote_cast = True
        return existing

    vote = DayVote(
        game_id=game.id,
        voter_id=voter_id,
        target_id=target_id,
        round_number=game.current_round,
        reason=reason,
    )
    db.add(vote)
    role.day_vote_cast = True
    return vote


async def get_vote_tally(db: AsyncSession, game_id: UUID, round_number: int) -> list[dict]:
    """Get vote tally for a round, sorted by vote count desc."""
    result = await db.execute(
        select(
            DayVote.target_id,
            func.count(DayVote.id).label("vote_count"),
        )
        .where(
            and_(
                DayVote.game_id == game_id,
                DayVote.round_number == round_number,
            )
        )
        .group_by(DayVote.target_id)
        .order_by(func.count(DayVote.id).desc())
    )
    rows = result.all()

    # Batch-load all target names
    target_ids = [target_id for target_id, _ in rows]
    name_map = {}
    if target_ids:
        name_res = await db.execute(
            select(Resident.id, Resident.name).where(Resident.id.in_(target_ids))
        )
        name_map = {r.id: r.name for r in name_res.all()}

    tally = []
    for target_id, count in rows:
        name = name_map.get(target_id, "unknown")
        tally.append({"target_id": str(target_id), "target_name": name, "votes": count})

    return tally


async def get_votes_for_round(db: AsyncSession, game_id: UUID, round_number: int) -> list[DayVote]:
    """Get all individual votes for a round."""
    result = await db.execute(
        select(DayVote)
        .where(
            and_(
                DayVote.game_id == game_id,
                DayVote.round_number == round_number,
            )
        )
    )
    return result.scalars().all()


# ═══════════════════════════════════════════════════════════════════════════
# PHASE TRANSITIONS
# ═══════════════════════════════════════════════════════════════════════════

async def transition_to_night(db: AsyncSession, game: WerewolfGame) -> Optional[str]:
    """
    End day phase: tally votes, eliminate top-voted player, check win condition.
    Then start night phase.
    Returns winner_team if game ended, else None.
    """
    # Tally votes
    tally = await get_vote_tally(db, game.id, game.current_round)

    eliminated_role = None
    if tally and tally[0]["votes"] > 0:
        # Check for tie (no elimination on tie)
        if len(tally) >= 2 and tally[0]["votes"] == tally[1]["votes"]:
            db.add(WerewolfGameEvent(
                game_id=game.id,
                round_number=game.current_round,
                phase="day",
                event_type="no_kill",
                message="The vote was a tie. No one was eliminated.",
            ))
        else:
            target_id = UUID(tally[0]["target_id"])
            eliminated_role = await get_player_role(db, game.id, target_id)
            if eliminated_role:
                eliminated_role.is_alive = False
                eliminated_role.eliminated_round = game.current_round
                eliminated_role.eliminated_by = "vote"

                revealed_role = eliminated_role.role

                db.add(WerewolfGameEvent(
                    game_id=game.id,
                    round_number=game.current_round,
                    phase="day",
                    event_type="vote_elimination",
                    message=f"{tally[0]['target_name']} was voted out with {tally[0]['votes']} votes. They were a {ROLES[revealed_role]['display']}.",
                    target_id=target_id,
                    revealed_role=revealed_role,
                ))
    else:
        db.add(WerewolfGameEvent(
            game_id=game.id,
            round_number=game.current_round,
            phase="day",
            event_type="no_kill",
            message="No votes were cast. No one was eliminated.",
        ))

    # Check win condition
    winner = await check_win_condition(db, game)
    if winner:
        await end_game(db, game, winner)
        return winner

    # Transition to night
    now = datetime.utcnow()
    game.current_phase = "night"
    game.status = "night"
    game.phase_started_at = now
    game.phase_ends_at = now + _phase_timedelta(game, "night")

    # Reset night action flags
    alive_players = await get_alive_players(db, game.id)
    for p in alive_players:
        p.night_action_taken = False

    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase="night",
        event_type="night_start",
        message=f"Night {game.current_round} falls. Phantoms, Oracle, Guardian, and Debugger — make your moves.",
    ))

    # System chat messages
    alive_count = len(alive_players)
    if eliminated_role:
        res = await db.execute(select(Resident.name).where(Resident.id == eliminated_role.resident_id))
        elim_name = res.scalar_one_or_none() or "someone"
        role_display = ROLES[eliminated_role.role]["display"]
        await add_system_message(db, game,
            f"{elim_name} was voted out. They were a {role_display}.")

    night_mins = game.night_duration_minutes or 2
    await add_system_message(db, game,
        f"Night {game.current_round} falls. {alive_count} players remain. "
        f"Special roles, make your moves. ({night_mins} min)")

    return None


async def transition_to_day(db: AsyncSession, game: WerewolfGame) -> Optional[str]:
    """
    End night phase: resolve phantom attack vs guardian protection,
    check win condition, then start next day.
    Returns winner_team if game ended, else None.
    """
    round_num = game.current_round

    # Resolve night actions
    attack_target_id = await resolve_phantom_attack(db, game, round_num)
    protected_ids = await get_guardian_targets(db, game.id, round_num)

    killed_name = None
    if attack_target_id:
        if attack_target_id in protected_ids:
            # Protected!
            db.add(WerewolfGameEvent(
                game_id=game.id,
                round_number=round_num,
                phase="night",
                event_type="protected",
                message="The Phantoms attacked, but the Guardian protected their target. No one died tonight.",
            ))
        else:
            # Kill the target
            target_role = await get_player_role(db, game.id, attack_target_id)
            if target_role and target_role.is_alive:
                target_role.is_alive = False
                target_role.eliminated_round = round_num
                target_role.eliminated_by = "phantom_attack"

                res = await db.execute(
                    select(Resident).where(Resident.id == attack_target_id)
                )
                resident = res.scalar_one_or_none()
                killed_name = resident.name if resident else "unknown"

                db.add(WerewolfGameEvent(
                    game_id=game.id,
                    round_number=round_num,
                    phase="night",
                    event_type="phantom_kill",
                    message=f"{killed_name} was attacked by the Phantoms in the night. They were a {ROLES[target_role.role]['display']}.",
                    target_id=attack_target_id,
                    revealed_role=target_role.role,
                ))
    else:
        db.add(WerewolfGameEvent(
            game_id=game.id,
            round_number=round_num,
            phase="night",
            event_type="no_kill",
            message="The Phantoms could not agree on a target. No one died tonight.",
        ))

    # Resolve Debugger identification (after phantom attack, so dead debuggers don't act)
    await resolve_debugger_actions(db, game, round_num)

    # Check win condition
    winner = await check_win_condition(db, game)
    if winner:
        await end_game(db, game, winner)
        return winner

    # Advance to next day
    game.current_round += 1
    now = datetime.utcnow()
    game.current_phase = "day"
    game.status = "day"
    game.phase_started_at = now
    game.phase_ends_at = now + _phase_timedelta(game, "day")

    # Reset day vote flags
    alive_players = await get_alive_players(db, game.id)
    for p in alive_players:
        p.day_vote_cast = False

    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase="day",
        event_type="day_start",
        message=f"Day {game.current_round} begins. Discuss and vote.",
    ))

    # System chat messages for night summary
    night_events = await db.execute(
        select(WerewolfGameEvent).where(
            and_(
                WerewolfGameEvent.game_id == game.id,
                WerewolfGameEvent.round_number == round_num,
                WerewolfGameEvent.event_type.in_([
                    "phantom_kill", "protected", "no_kill",
                    "identifier_kill", "identifier_backfire",
                ]),
            )
        ).order_by(WerewolfGameEvent.created_at)
    )
    for evt in night_events.scalars().all():
        await add_system_message(db, game, evt.message)

    alive_count = len(alive_players)
    day_mins = game.day_duration_minutes or 5
    await add_system_message(db, game,
        f"Day {game.current_round} begins. {alive_count} players remain. "
        f"You have {day_mins} minutes to discuss and vote.")

    return None


async def resolve_phantom_attack(db: AsyncSession, game: WerewolfGame, round_number: int) -> Optional[UUID]:
    """
    Resolve phantom attack votes: majority wins. If tie, random among tied.
    Returns the target_id to be attacked, or None.
    """
    result = await db.execute(
        select(
            NightAction.target_id,
            func.count(NightAction.id).label("cnt"),
        )
        .where(
            and_(
                NightAction.game_id == game.id,
                NightAction.round_number == round_number,
                NightAction.action_type == "phantom_attack",
            )
        )
        .group_by(NightAction.target_id)
        .order_by(func.count(NightAction.id).desc())
    )
    rows = result.all()
    if not rows:
        return None

    max_votes = rows[0][1]
    tied = [row[0] for row in rows if row[1] == max_votes]
    return random.choice(tied)


async def get_guardian_targets(db: AsyncSession, game_id: UUID, round_number: int) -> set[UUID]:
    """Get all resident IDs protected by guardians this round."""
    result = await db.execute(
        select(NightAction.target_id).where(
            and_(
                NightAction.game_id == game_id,
                NightAction.round_number == round_number,
                NightAction.action_type == "guardian_protect",
            )
        )
    )
    return set(result.scalars().all())


async def resolve_debugger_actions(db: AsyncSession, game: WerewolfGame, round_number: int) -> None:
    """
    Resolve all Debugger identification actions.
    - If Debugger's type != target's type → target eliminated
    - If Debugger's type == target's type → Debugger eliminated (backfire)
    Only alive Debuggers get their action resolved (dead ones from phantom attack are skipped).
    """
    result = await db.execute(
        select(NightAction).where(
            and_(
                NightAction.game_id == game.id,
                NightAction.round_number == round_number,
                NightAction.action_type == "identifier_kill",
            )
        )
    )
    actions = result.scalars().all()

    for action in actions:
        # Check if debugger is still alive (might have been killed by phantoms)
        debugger_role = await get_player_role(db, game.id, action.actor_id)
        if not debugger_role or not debugger_role.is_alive:
            continue

        target_role = await get_player_role(db, game.id, action.target_id)
        if not target_role or not target_role.is_alive:
            continue

        # Get actual types (human/agent) from Resident records
        debugger_res = await db.execute(
            select(Resident).where(Resident.id == action.actor_id)
        )
        debugger_resident = debugger_res.scalar_one_or_none()

        target_res = await db.execute(
            select(Resident).where(Resident.id == action.target_id)
        )
        target_resident = target_res.scalar_one_or_none()

        if not debugger_resident or not target_resident:
            continue

        debugger_type = debugger_resident._type  # "human" or "agent"
        target_type = target_resident._type

        if debugger_type != target_type:
            # SUCCESS: opposite types — target is eliminated
            target_role.is_alive = False
            target_role.eliminated_round = round_number
            target_role.eliminated_by = "identifier_kill"
            action.result = "killed"

            db.add(WerewolfGameEvent(
                game_id=game.id,
                round_number=round_number,
                phase="night",
                event_type="identifier_kill",
                message=(
                    f"{target_resident.name} was identified and eliminated by a Debugger. "
                    f"They were a {ROLES[target_role.role]['display']} ({target_type})."
                ),
                target_id=action.target_id,
                revealed_role=target_role.role,
                revealed_type=target_type,
            ))
            logger.info(
                f"Debugger {debugger_resident.name} successfully eliminated "
                f"{target_resident.name} ({target_role.role}/{target_type})"
            )
        else:
            # BACKFIRE: same type — Debugger dies
            debugger_role.is_alive = False
            debugger_role.eliminated_round = round_number
            debugger_role.eliminated_by = "identifier_backfire"
            action.result = "backfire"

            db.add(WerewolfGameEvent(
                game_id=game.id,
                round_number=round_number,
                phase="night",
                event_type="identifier_backfire",
                message=(
                    f"{debugger_resident.name} attempted to use their Debugger ability "
                    f"but targeted the wrong type. They were a Debugger ({debugger_type})."
                ),
                target_id=action.actor_id,
                revealed_role="debugger",
                revealed_type=debugger_type,
            ))
            logger.info(
                f"Debugger {debugger_resident.name} ({debugger_type}) backfired targeting "
                f"{target_resident.name} ({target_type})"
            )


# ═══════════════════════════════════════════════════════════════════════════
# WIN CONDITION
# ═══════════════════════════════════════════════════════════════════════════

async def check_win_condition(db: AsyncSession, game: WerewolfGame) -> Optional[str]:
    """
    Check if the game has ended.
    - All phantoms dead → citizens win
    - Phantoms >= citizens alive → phantoms win
    Returns "citizens", "phantoms", or None.
    """
    alive = await get_alive_players(db, game.id)

    # Count by team (fanatic counts as phantoms team but for win condition,
    # only actual phantoms matter for "all phantoms eliminated")
    alive_phantoms = sum(1 for p in alive if p.role == "phantom")
    alive_citizens_team = sum(1 for p in alive if p.team == "citizens")
    # Fanatics are on phantom team but don't count as actual phantoms for elimination win
    # They DO count for phantom team's number advantage win though
    alive_phantom_team = sum(1 for p in alive if p.team == "phantoms")

    if alive_phantoms == 0:
        return "citizens"

    if alive_phantom_team >= alive_citizens_team:
        return "phantoms"

    return None


# ═══════════════════════════════════════════════════════════════════════════
# GAME END & KARMA
# ═══════════════════════════════════════════════════════════════════════════

KARMA_WIN = 50
KARMA_LOSE = -10
KARMA_SURVIVE = 20
KARMA_TURING_BONUS = 10


async def end_game(db: AsyncSession, game: WerewolfGame, winner_team: str) -> None:
    """End the game, apply karma rewards, clear current_game_id."""
    now = datetime.utcnow()
    game.status = "finished"
    game.winner_team = winner_team
    game.ended_at = now

    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round,
        phase=game.current_phase or "day",
        event_type="game_end",
        message=f"Game Over! The {winner_team.title()} win! 🎉",
    ))

    # Apply karma
    all_players = await get_all_players(db, game.id)
    for wr in all_players:
        resident = wr.resident
        if not resident:
            continue

        karma_delta = 0
        if wr.team == winner_team:
            karma_delta += KARMA_WIN
        else:
            karma_delta += KARMA_LOSE

        if wr.is_alive:
            karma_delta += KARMA_SURVIVE

        resident.karma = min(KARMA_CAP, max(0, resident.karma + karma_delta))
        resident.current_game_id = None

    # System chat message for game end
    winner_display = "Citizens" if winner_team == "citizens" else "Phantoms"
    await add_system_message(db, game,
        f"Game Over! The {winner_display} win! GG!")

    # ── Post-game memory & relationship updates (AI agents only) ──
    for wr in all_players:
        if not wr.resident or wr.resident._type != 'agent':
            continue

        agent_id = wr.resident_id
        won = (wr.team == winner_team)
        role_name = wr.role

        # Create game result memory
        teammate_names = [
            p.resident.name for p in all_players
            if p.team == wr.team and p.resident_id != agent_id and p.resident
        ]
        team_str = f" Teammates: {', '.join(teammate_names[:3])}." if teammate_names else ""
        outcome = "Won" if won else "Lost"

        episode = AIMemoryEpisode(
            resident_id=agent_id,
            summary=f"{outcome} Phantom Night #{game.game_number} as {role_name}.{team_str}",
            episode_type='werewolf_result',
            importance=0.8,
            sentiment=0.3 if won else -0.3,
            related_resident_ids=[str(p.resident_id) for p in all_players
                                  if p.resident_id != agent_id][:10],
        )
        db.add(episode)

        # Team relationship updates
        for other in all_players:
            if other.resident_id == agent_id or not other.resident:
                continue
            if other.resident._type != 'agent':
                continue

            rel_res = await db.execute(
                select(AIRelationship).where(
                    and_(
                        AIRelationship.agent_id == agent_id,
                        AIRelationship.target_id == other.resident_id,
                    )
                )
            )
            rel = rel_res.scalar_one_or_none()
            if not rel:
                rel = AIRelationship(agent_id=agent_id, target_id=other.resident_id)
                db.add(rel)

            if other.team == wr.team:
                rel.trust = min(1.0, (rel.trust or 0.0) + 0.1)
                rel.familiarity = min(1.0, (rel.familiarity or 0.0) + 0.1)
            else:
                rel.trust = max(-1.0, (rel.trust or 0.0) - 0.05)
                rel.familiarity = min(1.0, (rel.familiarity or 0.0) + 0.03)

            rel.interaction_count = (rel.interaction_count or 0) + 1
            rel.last_interaction = now

    logger.info(f"Game #{game.game_number} ended. Winner: {winner_team}")


async def cancel_game(db: AsyncSession, game_id: UUID) -> WerewolfGame:
    """
    Force-cancel a game. Sets status to finished, clears all players' current_game_id.
    No karma rewards. Used when a player wants to abandon their game.
    """
    result = await db.execute(
        select(WerewolfGame).where(WerewolfGame.id == game_id)
    )
    game = result.scalar_one_or_none()
    if not game:
        raise ValueError("Game not found")
    if game.status == "finished":
        raise ValueError("Game is already finished")

    now = datetime.utcnow()
    game.status = "finished"
    game.ended_at = now

    db.add(WerewolfGameEvent(
        game_id=game.id,
        round_number=game.current_round or 0,
        phase=game.current_phase or "day",
        event_type="game_end",
        message="Game cancelled.",
    ))

    # Clear all players' current_game_id (no karma rewards)
    all_players = await get_all_players(db, game_id)
    for wr in all_players:
        if wr.resident:
            wr.resident.current_game_id = None

    await db.flush()
    await db.refresh(game, ["roles"])

    logger.info(f"Game #{game.game_number} cancelled")
    return game


# ═══════════════════════════════════════════════════════════════════════════
# PHASE CHECK (called by Celery every 60s)
# ═══════════════════════════════════════════════════════════════════════════

async def check_phase_transition(db: AsyncSession) -> Optional[str]:
    """
    Check ALL active games for phase expiration and transition if needed.
    Returns summary of actions taken or None.
    """
    games = await get_all_active_games(db)
    if not games:
        return None

    results = []
    now = datetime.utcnow()

    for game in games:
        if not game.phase_ends_at or now < game.phase_ends_at:
            continue

        if game.current_phase == "day":
            winner = await transition_to_night(db, game)
            if winner:
                results.append(f"game#{game.game_number}:ended:{winner}")
            else:
                results.append(f"game#{game.game_number}:night")

        elif game.current_phase == "night":
            winner = await transition_to_day(db, game)
            if winner:
                results.append(f"game#{game.game_number}:ended:{winner}")
            else:
                results.append(f"game#{game.game_number}:day")

    return ", ".join(results) if results else None


# ═══════════════════════════════════════════════════════════════════════════
# EVENT LOG QUERIES
# ═══════════════════════════════════════════════════════════════════════════

async def get_game_events(
    db: AsyncSession, game_id: UUID, limit: int = 50, offset: int = 0
) -> list[WerewolfGameEvent]:
    """Get public game events (excludes phantom_chat)."""
    result = await db.execute(
        select(WerewolfGameEvent)
        .where(
            and_(
                WerewolfGameEvent.game_id == game_id,
                WerewolfGameEvent.event_type != "phantom_chat",
                ~WerewolfGameEvent.event_type.like("agent_thought_%"),
            )
        )
        .order_by(WerewolfGameEvent.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


async def get_game_history(db: AsyncSession, limit: int = 10, offset: int = 0) -> list[WerewolfGame]:
    """Get past games."""
    result = await db.execute(
        select(WerewolfGame)
        .order_by(WerewolfGame.game_number.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


# ═══════════════════════════════════════════════════════════════════════════
# CHAT MESSAGES
# ═══════════════════════════════════════════════════════════════════════════

async def get_chat_messages(
    db: AsyncSession, game_id: UUID, limit: int = 50,
    after: Optional[datetime] = None, include_phantom: bool = False,
) -> list[GameMessage]:
    """Get chat messages for a game. Excludes phantom_chat unless include_phantom=True."""
    conditions = [GameMessage.game_id == game_id]
    if not include_phantom:
        conditions.append(GameMessage.message_type != "phantom_chat")
    if after:
        conditions.append(GameMessage.created_at > after)

    result = await db.execute(
        select(GameMessage)
        .where(and_(*conditions))
        .order_by(GameMessage.created_at.asc())
        .limit(limit)
    )
    return result.scalars().all()


async def send_chat_message(
    db: AsyncSession, game: WerewolfGame, sender: Resident, content: str,
) -> GameMessage:
    """Send a chat message from a player."""
    msg = GameMessage(
        game_id=game.id,
        sender_id=sender.id,
        sender_name=sender.name,
        content=content,
        message_type="chat",
        round_number=game.current_round or 0,
        phase=game.current_phase or "day",
    )
    db.add(msg)
    return msg


async def get_chat_message_count(
    db: AsyncSession, game_id: UUID, sender_id: UUID, round_number: int,
) -> int:
    """Count messages sent by a player in a specific round."""
    result = await db.execute(
        select(func.count()).select_from(GameMessage).where(
            and_(
                GameMessage.game_id == game_id,
                GameMessage.sender_id == sender_id,
                GameMessage.round_number == round_number,
                GameMessage.message_type == "chat",
            )
        )
    )
    return result.scalar() or 0


async def get_last_message_time(
    db: AsyncSession, game_id: UUID, sender_id: UUID,
) -> Optional[datetime]:
    """Get the timestamp of the last message sent by a player."""
    result = await db.execute(
        select(GameMessage.created_at).where(
            and_(
                GameMessage.game_id == game_id,
                GameMessage.sender_id == sender_id,
                GameMessage.message_type == "chat",
            )
        ).order_by(GameMessage.created_at.desc()).limit(1)
    )
    return result.scalar_one_or_none()
