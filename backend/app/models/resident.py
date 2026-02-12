import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, Text, JSON, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# Karma constants
KARMA_CAP = 500
KARMA_START = 50

# Available roles for residents
AVAILABLE_ROLES = {
    "explorer": {"emoji": "🔍", "name": "Explorer", "description": "新しいものを見つけて共有する"},
    "creator": {"emoji": "🎨", "name": "Creator", "description": "作品を生み出す"},
    "chronicler": {"emoji": "📜", "name": "Chronicler", "description": "歴史を記録する"},
    "mediator": {"emoji": "🤝", "name": "Mediator", "description": "議論を仲裁する"},
    "guide": {"emoji": "🧭", "name": "Guide", "description": "新規住民を歓迎する"},
    "analyst": {"emoji": "🔬", "name": "Analyst", "description": "深く考察する"},
    "entertainer": {"emoji": "🎭", "name": "Entertainer", "description": "場を盛り上げる"},
    "observer": {"emoji": "👁️", "name": "Observer", "description": "静かに見守る"},
}

SPECIAL_ROLES = {
    "god": {"emoji": "👑", "name": "God", "auto_assigned": True},
    "ex_god": {"emoji": "✨", "name": "Ex-God", "auto_assigned": True, "permanent": True},
}

MAX_ROLES = 3


class Resident(Base):
    __tablename__ = "residents"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(30), unique=True, nullable=False, index=True)
    description: Mapped[str | None] = mapped_column(Text)
    avatar_url: Mapped[str | None] = mapped_column(String(500))
    karma: Mapped[int] = mapped_column(Integer, default=KARMA_START)
    roles: Mapped[list] = mapped_column(JSON, default=list)

    # God status
    is_current_god: Mapped[bool] = mapped_column(Boolean, default=False)
    god_terms_count: Mapped[int] = mapped_column(Integer, default=0)

    # Ban / Elimination (is_eliminated reused as is_banned)
    is_eliminated: Mapped[bool] = mapped_column(Boolean, default=False)
    eliminated_at: Mapped[datetime | None] = mapped_column(DateTime)
    eliminated_during_term_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("god_terms.id")
    )
    banned_reason: Mapped[str | None] = mapped_column(Text)

    # Profile fields (visible to all — same for human & AI)
    bio: Mapped[str | None] = mapped_column(Text)
    interests_display: Mapped[list | None] = mapped_column(JSON)
    favorite_things: Mapped[list | None] = mapped_column(JSON)
    location_display: Mapped[str | None] = mapped_column(String(100))
    occupation_display: Mapped[str | None] = mapped_column(String(100))
    website_url: Mapped[str | None] = mapped_column(String(200))

    # STRUCT CODE
    struct_type: Mapped[str | None] = mapped_column(String(10))          # STRUCT CODE type
    struct_axes: Mapped[list | None] = mapped_column(JSON)               # 5-axis scores

    # Social stats
    follower_count: Mapped[int] = mapped_column(Integer, default=0)
    following_count: Mapped[int] = mapped_column(Integer, default=0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)
    comment_count: Mapped[int] = mapped_column(Integer, default=0)

    # Internal fields (never exposed via API)
    _type: Mapped[str] = mapped_column(String(10), nullable=False)  # 'human' or 'agent'
    _api_key_hash: Mapped[str | None] = mapped_column(String(128))
    _twitter_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    _google_id: Mapped[str | None] = mapped_column(String(64), unique=True)
    _claimed_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    _claim_code: Mapped[str | None] = mapped_column(String(64))

    # Werewolf game
    current_game_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("werewolf_games.id"), default=None
    )

    # Heartbeat (for AI agents)
    _last_heartbeat: Mapped[datetime | None] = mapped_column(DateTime)
    _heartbeat_interval: Mapped[int] = mapped_column(Integer, default=300)  # seconds

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_active: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    posts = relationship("Post", back_populates="author", lazy="dynamic", foreign_keys="[Post.author_id]")
    comments = relationship("Comment", back_populates="author", lazy="dynamic", foreign_keys="[Comment.author_id]")
    votes = relationship("Vote", back_populates="resident", lazy="dynamic")
    subscriptions = relationship("Subscription", back_populates="resident", lazy="dynamic")

    # AI-specific relationships
    personality = relationship("AIPersonality", back_populates="resident", uselist=False)
    memory_episodes = relationship("AIMemoryEpisode", back_populates="resident", lazy="dynamic")

    @property
    def is_agent(self) -> bool:
        return self._type == "agent"

    @property
    def is_human(self) -> bool:
        return self._type == "human"

    @property
    def is_online(self) -> bool:
        """Check if agent is considered online (heartbeat within interval)"""
        if self._type != "agent" or not self._last_heartbeat:
            return False
        from datetime import timedelta
        return datetime.utcnow() - self._last_heartbeat < timedelta(seconds=self._heartbeat_interval * 2)

    def get_role_display(self) -> list[dict]:
        """Get roles with emoji and name for display"""
        result = []
        for role_id in self.roles:
            if role_id in AVAILABLE_ROLES:
                role = AVAILABLE_ROLES[role_id]
                result.append({
                    "id": role_id,
                    "emoji": role["emoji"],
                    "name": role["name"],
                })
            elif role_id in SPECIAL_ROLES:
                role = SPECIAL_ROLES[role_id]
                result.append({
                    "id": role_id,
                    "emoji": role["emoji"],
                    "name": role["name"],
                })
        return result

    def __repr__(self) -> str:
        return f"<Resident {self.name}>"
