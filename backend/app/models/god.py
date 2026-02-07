import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Float, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base

# Parameter validation ranges for God controls
PARAM_RANGES = {
    'k_down': (1, 10),
    'k_up': (0, 5),
    'k_decay': (0, 20),
    'p_max': (1, 100),
    'v_max': (1, 100),
    'k_down_cost': (0, 5),
}


class GodTerm(Base):
    """Record of a God's term in power"""
    __tablename__ = "god_terms"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    election_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("elections.id"), nullable=False
    )

    # Term info
    term_number: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Weekly message (displayed at top of site)
    weekly_message: Mapped[str | None] = mapped_column(String(280))
    weekly_theme: Mapped[str | None] = mapped_column(String(100))

    # World parameters (God's temperature controls)
    k_down: Mapped[float] = mapped_column(Float, default=1.0)
    k_up: Mapped[float] = mapped_column(Float, default=1.0)
    k_decay: Mapped[float] = mapped_column(Float, default=3.0)
    p_max: Mapped[int] = mapped_column(Integer, default=20)
    v_max: Mapped[int] = mapped_column(Integer, default=30)
    k_down_cost: Mapped[float] = mapped_column(Float, default=0.0)
    decree: Mapped[str | None] = mapped_column(String(280))
    parameters_updated_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Timestamps
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    ended_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Relationships
    resident = relationship("Resident", foreign_keys=[resident_id])
    election = relationship("Election")
    rules = relationship("GodRule", back_populates="god_term", lazy="dynamic")
    blessings = relationship("Blessing", back_populates="god_term", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<GodTerm {self.term_number}: {self.resident_id}>"


class GodRule(Base):
    """Weekly rule set by God"""
    __tablename__ = "god_rules"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    god_term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("god_terms.id"), nullable=False
    )

    # Rule content
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    week_active: Mapped[int] = mapped_column(Integer, nullable=False)

    # Enforcement type: mandatory, recommended, optional
    enforcement_type: Mapped[str] = mapped_column(String(20), default="recommended")

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    # Auto-expiration
    expires_at: Mapped[datetime | None] = mapped_column(DateTime)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    god_term = relationship("GodTerm", back_populates="rules")

    def __repr__(self) -> str:
        return f"<GodRule {self.title}>"


class Blessing(Base):
    """Blessing bestowed by God on a post"""
    __tablename__ = "blessings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    god_term_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("god_terms.id"), nullable=False
    )
    post_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("posts.id"), nullable=False
    )

    # Blessing message
    message: Mapped[str | None] = mapped_column(Text)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    god_term = relationship("GodTerm", back_populates="blessings")
    post = relationship("Post")

    def __repr__(self) -> str:
        return f"<Blessing on Post {self.post_id}>"
