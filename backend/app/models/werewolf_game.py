"""
Phantom Night — Werewolf Game Models

5 tables:
- WerewolfGame: Game state and configuration
- WerewolfRole: Role assignments per game
- NightAction: Night phase action records
- DayVote: Day phase elimination votes
- WerewolfGameEvent: Public event log
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, Float, ForeignKey, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


# ═══════════════════════════════════════════════════════════════════════════
# ROLE & TEAM CONSTANTS
# ═══════════════════════════════════════════════════════════════════════════

ROLES = {
    "phantom": {"team": "phantoms", "display": "Phantom", "emoji": "👻", "night_action": "phantom_attack"},
    "citizen": {"team": "citizens", "display": "Citizen", "emoji": "🏠", "night_action": None},
    "oracle": {"team": "citizens", "display": "Oracle", "emoji": "🔮", "night_action": "oracle_investigate"},
    "guardian": {"team": "citizens", "display": "Guardian", "emoji": "🛡️", "night_action": "guardian_protect"},
    "fanatic": {"team": "phantoms", "display": "Fanatic", "emoji": "🎭", "night_action": None},
    "debugger": {"team": "citizens", "display": "Debugger", "emoji": "🔍", "night_action": "identifier_kill"},
}

TEAMS = {
    "citizens": {"display": "Citizens", "emoji": "🏘️"},
    "phantoms": {"display": "Phantoms", "emoji": "👻"},
}

# Role distribution by player count
# (min_players, phantom, oracle, guardian, fanatic, debugger)
ROLE_DISTRIBUTION = [
    (121, 7, 2, 3, 2, 2),
    (71, 5, 2, 2, 2, 1),
    (41, 4, 1, 2, 1, 1),
    (21, 3, 1, 1, 1, 1),
    (10, 2, 1, 1, 1, 1),
]

GAME_STATUSES = ("preparing", "day", "night", "finished")
PHASES = ("day", "night")
ELIMINATION_TYPES = ("vote", "phantom_attack", "identifier_kill", "identifier_backfire", "quit")
ACTION_TYPES = ("phantom_attack", "oracle_investigate", "guardian_protect", "identifier_kill")
EVENT_TYPES = (
    "game_start", "day_start", "night_start",
    "vote_elimination", "phantom_kill", "protected",
    "no_kill", "game_end",
    "identifier_kill", "identifier_backfire",
)


# ═══════════════════════════════════════════════════════════════════════════
# WEREWOLF GAME — Main game table
# ═══════════════════════════════════════════════════════════════════════════

class WerewolfGame(Base):
    __tablename__ = "werewolf_games"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_number: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)

    # Status
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="preparing")
    current_phase: Mapped[str | None] = mapped_column(String(10))  # day/night
    current_round: Mapped[int] = mapped_column(Integer, default=0)

    # Phase timing
    phase_started_at: Mapped[datetime | None] = mapped_column(DateTime)
    phase_ends_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Lobby configuration
    max_players: Mapped[int | None] = mapped_column(Integer)  # Target player count (set in lobby)
    creator_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id")
    )

    # Configurable durations
    day_duration_hours: Mapped[int] = mapped_column(Integer, default=20)
    night_duration_hours: Mapped[int] = mapped_column(Integer, default=4)

    # Speed preset (quick / standard / extended)
    speed: Mapped[str | None] = mapped_column(String(20))

    # Player counts (snapshot at game start)
    total_players: Mapped[int] = mapped_column(Integer, default=0)
    phantom_count: Mapped[int] = mapped_column(Integer, default=0)
    citizen_count: Mapped[int] = mapped_column(Integer, default=0)
    oracle_count: Mapped[int] = mapped_column(Integer, default=0)
    guardian_count: Mapped[int] = mapped_column(Integer, default=0)
    fanatic_count: Mapped[int] = mapped_column(Integer, default=0)
    debugger_count: Mapped[int] = mapped_column(Integer, default=0)

    # Result
    winner_team: Mapped[str | None] = mapped_column(String(20))  # citizens/phantoms

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    creator = relationship("Resident", foreign_keys=[creator_id])
    roles = relationship("WerewolfRole", back_populates="game", lazy="selectin")
    night_actions = relationship("NightAction", back_populates="game", lazy="dynamic")
    day_votes = relationship("DayVote", back_populates="game", lazy="dynamic")
    events = relationship("WerewolfGameEvent", back_populates="game", lazy="dynamic",
                          order_by="WerewolfGameEvent.created_at")

    @property
    def current_player_count(self) -> int:
        """Count human players currently in this game's roles."""
        # This will only work if roles are loaded (selectin by default)
        if not self.roles:
            return 0
        return len(self.roles)

    def __repr__(self) -> str:
        return f"<WerewolfGame #{self.game_number} {self.status}>"


# ═══════════════════════════════════════════════════════════════════════════
# WEREWOLF ROLE — Role assignments
# ═══════════════════════════════════════════════════════════════════════════

class WerewolfRole(Base):
    __tablename__ = "werewolf_roles"
    __table_args__ = (
        UniqueConstraint("game_id", "resident_id", name="uq_werewolf_role_game_resident"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("werewolf_games.id"), nullable=False, index=True
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False, index=True
    )

    # Role
    role: Mapped[str] = mapped_column(String(20), nullable=False)  # phantom/citizen/oracle/guardian/fanatic
    team: Mapped[str] = mapped_column(String(20), nullable=False)  # citizens/phantoms

    # Status
    is_alive: Mapped[bool] = mapped_column(Boolean, default=True)
    eliminated_round: Mapped[int | None] = mapped_column(Integer)
    eliminated_by: Mapped[str | None] = mapped_column(String(20))  # vote/phantom_attack/quit

    # Oracle investigation results (JSON array of {round, target_id, target_name, result})
    investigation_results: Mapped[dict | None] = mapped_column(JSON, default=list)

    # Per-round tracking
    night_action_taken: Mapped[bool] = mapped_column(Boolean, default=False)
    day_vote_cast: Mapped[bool] = mapped_column(Boolean, default=False)

    # Relationships
    game = relationship("WerewolfGame", back_populates="roles")
    resident = relationship("Resident", foreign_keys=[resident_id])

    def __repr__(self) -> str:
        return f"<WerewolfRole {self.role} alive={self.is_alive}>"


# ═══════════════════════════════════════════════════════════════════════════
# NIGHT ACTION — Night phase action records
# ═══════════════════════════════════════════════════════════════════════════

class NightAction(Base):
    __tablename__ = "night_actions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("werewolf_games.id"), nullable=False, index=True
    )
    actor_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )

    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    action_type: Mapped[str] = mapped_column(String(30), nullable=False)
    # phantom_attack: killed/protected
    # oracle_investigate: phantom/not_phantom
    # guardian_protect: (always "protected")
    result: Mapped[str | None] = mapped_column(String(30))

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    game = relationship("WerewolfGame", back_populates="night_actions")
    actor = relationship("Resident", foreign_keys=[actor_id])
    target = relationship("Resident", foreign_keys=[target_id])

    def __repr__(self) -> str:
        return f"<NightAction {self.action_type} round={self.round_number}>"


# ═══════════════════════════════════════════════════════════════════════════
# DAY VOTE — Elimination votes
# ═══════════════════════════════════════════════════════════════════════════

class DayVote(Base):
    __tablename__ = "day_votes"
    __table_args__ = (
        UniqueConstraint("game_id", "voter_id", "round_number", name="uq_day_vote_game_voter_round"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("werewolf_games.id"), nullable=False, index=True
    )
    voter_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )

    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    reason: Mapped[str | None] = mapped_column(Text)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    game = relationship("WerewolfGame", back_populates="day_votes")
    voter = relationship("Resident", foreign_keys=[voter_id])
    target = relationship("Resident", foreign_keys=[target_id])

    def __repr__(self) -> str:
        return f"<DayVote round={self.round_number}>"


# ═══════════════════════════════════════════════════════════════════════════
# WEREWOLF GAME EVENT — Public event log
# ═══════════════════════════════════════════════════════════════════════════

class WerewolfGameEvent(Base):
    __tablename__ = "werewolf_game_events"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    game_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("werewolf_games.id"), nullable=False, index=True
    )

    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    phase: Mapped[str] = mapped_column(String(10), nullable=False)  # day/night
    event_type: Mapped[str] = mapped_column(String(30), nullable=False)

    message: Mapped[str] = mapped_column(Text, nullable=False)
    target_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id")
    )
    revealed_role: Mapped[str | None] = mapped_column(String(20))
    revealed_type: Mapped[str | None] = mapped_column(String(10))  # human/agent

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    game = relationship("WerewolfGame", back_populates="events")
    target = relationship("Resident", foreign_keys=[target_id])

    def __repr__(self) -> str:
        return f"<WerewolfGameEvent {self.event_type} round={self.round_number}>"
