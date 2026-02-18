import uuid
from datetime import datetime
from sqlalchemy import String, Integer, DateTime, Text, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from app.database import Base


class IndividualSubscription(Base):
    __tablename__ = "individual_subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), unique=True, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan_type: Mapped[str] = mapped_column(String(20), default="monthly")  # monthly / annual
    status: Mapped[str] = mapped_column(String(20), default="none")  # none / active / past_due / canceled
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now()
    )

    resident = relationship("Resident", foreign_keys=[resident_id])

    def __repr__(self) -> str:
        return f"<IndividualSubscription {self.resident_id} {self.status}>"


class ReportPurchase(Base):
    __tablename__ = "report_purchases"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    resident_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("residents.id"), nullable=False
    )
    report_type: Mapped[str] = mapped_column(String(30), nullable=False)  # work/romance/relationships/stress/growth/compatibility
    stripe_checkout_session_id: Mapped[str | None] = mapped_column(String(255))
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending / completed
    content: Mapped[str | None] = mapped_column(Text)  # cached report content
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )

    resident = relationship("Resident", foreign_keys=[resident_id])

    def __repr__(self) -> str:
        return f"<ReportPurchase {self.resident_id} {self.report_type} {self.status}>"


class OrgSubscription(Base):
    __tablename__ = "org_subscriptions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    company_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("companies.id"), unique=True, nullable=False
    )
    stripe_customer_id: Mapped[str | None] = mapped_column(String(255))
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(255))
    plan_type: Mapped[str] = mapped_column(String(20), default="monthly")  # monthly / annual
    status: Mapped[str] = mapped_column(String(20), default="none")  # none / active / past_due / canceled
    quantity: Mapped[int] = mapped_column(Integer, default=0)  # number of seats
    current_period_end: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime, onupdate=func.now()
    )

    company = relationship("Company", foreign_keys=[company_id])

    def __repr__(self) -> str:
        return f"<OrgSubscription {self.company_id} {self.status} qty={self.quantity}>"
