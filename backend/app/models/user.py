"""User model for OAuth-authenticated users who can create and manage agents."""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Index, Integer, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    display_name: Mapped[str] = mapped_column(String(200), nullable=False)
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)

    # OAuth provider info
    provider: Mapped[str] = mapped_column(String(20), nullable=False)  # "google", "github"
    provider_id: Mapped[str] = mapped_column(String(200), nullable=False)

    # Tier / entitlements
    is_premium: Mapped[bool] = mapped_column(Boolean, default=False)
    agent_slots: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    last_login: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        Index("ix_users_provider", "provider", "provider_id", unique=True),
    )
