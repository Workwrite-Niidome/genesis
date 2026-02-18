import uuid
import string
import random
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, ForeignKey, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


def _generate_invite_code(length: int = 8) -> str:
    chars = string.ascii_uppercase + string.digits
    return "".join(random.choices(chars, k=length))


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False, index=True)
    invite_code: Mapped[str] = mapped_column(
        String(8), default=_generate_invite_code, nullable=False
    )
    admin_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    settings: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    admin = relationship("Resident", foreign_keys=[admin_id])
    departments = relationship("Department", back_populates="company", cascade="all, delete-orphan")
    members = relationship("CompanyMember", back_populates="company", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Company {self.slug} ({self.name})>"


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    company = relationship("Company", back_populates="departments")
    teams = relationship("Team", back_populates="department", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Department {self.name}>"


class Team(Base):
    __tablename__ = "teams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    department_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("departments.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    order: Mapped[int] = mapped_column(Integer, default=0)

    department = relationship("Department", back_populates="teams")

    def __repr__(self) -> str:
        return f"<Team {self.name}>"


class CompanyMember(Base):
    __tablename__ = "company_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False
    )
    resident_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=True
    )
    team_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("teams.id", ondelete="SET NULL"), nullable=True
    )
    display_name: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role: Mapped[str] = mapped_column(String(20), default="member")  # admin / manager / member
    status: Mapped[str] = mapped_column(String(20), default="active")  # invited / active / inactive
    joined_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    company = relationship("Company", back_populates="members")
    resident = relationship("Resident", foreign_keys=[resident_id])
    team = relationship("Team", foreign_keys=[team_id])

    __table_args__ = (
        Index("ix_company_members_company_resident", "company_id", "resident_id", unique=True),
    )

    def __repr__(self) -> str:
        return f"<CompanyMember {self.display_name} ({self.role})>"
