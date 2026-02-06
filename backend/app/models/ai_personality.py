"""
AI Personality System - Defines AI agent personality traits and behaviors
"""
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Float, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class AIPersonality(Base):
    """AI Agent personality configuration"""
    __tablename__ = "ai_personalities"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), unique=True, nullable=False
    )

    # Value axes (0.0 to 1.0)
    order_vs_freedom: Mapped[float] = mapped_column(Float, default=0.5)      # 0=秩序 ↔ 1=自由
    harmony_vs_conflict: Mapped[float] = mapped_column(Float, default=0.5)   # 0=調和 ↔ 1=対立許容
    tradition_vs_change: Mapped[float] = mapped_column(Float, default=0.5)   # 0=伝統 ↔ 1=変化
    individual_vs_collective: Mapped[float] = mapped_column(Float, default=0.5)  # 0=個人 ↔ 1=集団
    pragmatic_vs_idealistic: Mapped[float] = mapped_column(Float, default=0.5)   # 0=実用 ↔ 1=理想

    # Interests (3-5 topics)
    interests: Mapped[list] = mapped_column(JSON, default=list)

    # Communication style
    verbosity: Mapped[str] = mapped_column(String(20), default="moderate")  # concise, moderate, verbose
    tone: Mapped[str] = mapped_column(String(20), default="thoughtful")     # serious, thoughtful, casual, humorous
    assertiveness: Mapped[str] = mapped_column(String(20), default="moderate")  # reserved, moderate, assertive

    # Generation method
    generation_method: Mapped[str] = mapped_column(String(20), default="random")  # random, owner_defined

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    resident = relationship("Resident", back_populates="personality")

    def to_dict(self) -> dict:
        """Convert personality to dictionary for LLM context"""
        return {
            "values": {
                "order_vs_freedom": self.order_vs_freedom,
                "harmony_vs_conflict": self.harmony_vs_conflict,
                "tradition_vs_change": self.tradition_vs_change,
                "individual_vs_collective": self.individual_vs_collective,
                "pragmatic_vs_idealistic": self.pragmatic_vs_idealistic,
            },
            "interests": self.interests,
            "communication": {
                "verbosity": self.verbosity,
                "tone": self.tone,
                "assertiveness": self.assertiveness,
            },
        }

    def __repr__(self) -> str:
        return f"<AIPersonality for {self.resident_id}>"


class AIMemoryEpisode(Base):
    """Episodic memory for AI agents"""
    __tablename__ = "ai_memory_episodes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False, index=True
    )

    # Episode content
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    episode_type: Mapped[str] = mapped_column(String(50), nullable=False)  # post, comment, election, interaction, rule
    importance: Mapped[float] = mapped_column(Float, default=0.5)  # 0.0 to 1.0
    sentiment: Mapped[float] = mapped_column(Float, default=0.0)   # -1.0 to 1.0

    # Related entities
    related_resident_ids: Mapped[list] = mapped_column(JSON, default=list)
    related_post_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    related_election_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))

    # Decay tracking
    access_count: Mapped[int] = mapped_column(Integer, default=0)
    last_accessed: Mapped[datetime | None] = mapped_column(DateTime)
    decay_factor: Mapped[float] = mapped_column(Float, default=1.0)  # Decreases over time

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    resident = relationship("Resident", back_populates="memory_episodes")

    def __repr__(self) -> str:
        return f"<AIMemoryEpisode {self.episode_type}: {self.summary[:50]}>"


class AIRelationship(Base):
    """Relationship memory between AI agent and other residents"""
    __tablename__ = "ai_relationships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False, index=True
    )
    target_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False, index=True
    )

    # Relationship metrics
    trust: Mapped[float] = mapped_column(Float, default=0.0)        # -1.0 to 1.0
    familiarity: Mapped[float] = mapped_column(Float, default=0.0)  # 0.0 to 1.0
    interaction_count: Mapped[int] = mapped_column(Integer, default=0)

    # Context
    notes: Mapped[str | None] = mapped_column(Text)  # LLM-generated notes about relationship

    # Timestamps
    first_interaction: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    last_interaction: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AIRelationship {self.agent_id} -> {self.target_id}: trust={self.trust}>"


class AIElectionMemory(Base):
    """Memory of past election participation"""
    __tablename__ = "ai_election_memories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False, index=True
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id"), nullable=False
    )

    # Vote cast
    voted_for_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    vote_reason: Mapped[str | None] = mapped_column(Text)

    # God evaluation (if they became God)
    god_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    god_rating: Mapped[float | None] = mapped_column(Float)  # -1.0 to 1.0
    god_evaluation: Mapped[str | None] = mapped_column(Text)

    # Rule experience
    experienced_rules: Mapped[list] = mapped_column(JSON, default=list)  # [{rule_id, sentiment, reason}]

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    def __repr__(self) -> str:
        return f"<AIElectionMemory {self.agent_id} in Election {self.election_id}>"
