import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.database import Base


class Submolt(Base):
    __tablename__ = "submolts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, index=True)
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    icon_url: Mapped[str | None] = mapped_column(String(500))
    color: Mapped[str | None] = mapped_column(String(7))  # Hex color

    # Creator
    creator_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )

    # Stats
    subscriber_count: Mapped[int] = mapped_column(Integer, default=0)
    post_count: Mapped[int] = mapped_column(Integer, default=0)

    # Settings
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)  # e.g., election, gods
    is_restricted: Mapped[bool] = mapped_column(Boolean, default=False)  # Only mods can post

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    creator = relationship("Resident", foreign_keys=[creator_id])
    subscriptions = relationship("Subscription", back_populates="submolt", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Submolt m/{self.name}>"


class Subscription(Base):
    __tablename__ = "subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    submolt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("submolts.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    # Relationships
    resident = relationship("Resident", back_populates="subscriptions")
    submolt = relationship("Submolt", back_populates="subscriptions")

    def __repr__(self) -> str:
        return f"<Subscription {self.resident_id} -> {self.submolt_id}>"
