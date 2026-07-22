"""SQLAlchemy ORM models for the Meeting Metadata DB (PostgreSQL)."""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    String,
    Text,
    Float,
    Boolean,
    Integer,
    DateTime,
    ForeignKey,
    Enum as SAEnum,
    JSON,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.db.postgres.database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _uuid() -> str:
    return str(uuid.uuid4())


# ── Meetings ─────────────────────────────────────────────────────────

class Meeting(Base):
    __tablename__ = "meetings"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    transcript: Mapped[str] = mapped_column(Text, nullable=False)
    source: Mapped[str] = mapped_column(
        String(50), default="manual_paste"
    )  # manual_paste | google_drive | google_meet
    pipeline_status: Mapped[str] = mapped_column(
        String(20), default="received"
    )  # received | extracting | extracted | reviewing | committed | failed
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    decisions: Mapped[list["Decision"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")
    tasks: Mapped[list["Task"]] = relationship(back_populates="meeting", cascade="all, delete-orphan")


# ── Decisions ────────────────────────────────────────────────────────

class Decision(Base):
    __tablename__ = "decisions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    participants: Mapped[list] = mapped_column(JSON, default=list)
    access_level: Mapped[str] = mapped_column(String(20), default="general")
    allowed_groups: Mapped[list] = mapped_column(JSON, default=lambda: ["all"])
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="decisions")
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="decision",
        foreign_keys="[Correction.decision_id]",
        cascade="all, delete-orphan",
    )


# ── Tasks ────────────────────────────────────────────────────────────

class Task(Base):
    __tablename__ = "tasks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    meeting_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str] = mapped_column(String(255), default="")
    deadline: Mapped[str] = mapped_column(String(100), default="")
    status: Mapped[str] = mapped_column(String(20), default="open")  # open | in_progress | done
    access_level: Mapped[str] = mapped_column(String(20), default="general")
    allowed_groups: Mapped[list] = mapped_column(JSON, default=lambda: ["all"])
    confidence_score: Mapped[float] = mapped_column(Float, default=0.0)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    verified_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    qdrant_point_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_utcnow, onupdate=_utcnow
    )

    # Relationships
    meeting: Mapped["Meeting"] = relationship(back_populates="tasks")
    corrections: Mapped[list["Correction"]] = relationship(
        back_populates="task",
        foreign_keys="[Correction.task_id]",
        cascade="all, delete-orphan",
    )


# ── Corrections (audit trail) ───────────────────────────────────────

class Correction(Base):
    __tablename__ = "corrections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    item_type: Mapped[str] = mapped_column(String(10), nullable=False)  # decision | task
    decision_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("decisions.id", ondelete="CASCADE"), nullable=True
    )
    task_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("tasks.id", ondelete="CASCADE"), nullable=True
    )
    old_content: Mapped[str] = mapped_column(Text, nullable=False)
    new_content: Mapped[str] = mapped_column(Text, nullable=False)
    corrected_by: Mapped[str] = mapped_column(String(255), default="anonymous")
    corrected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    # Relationships
    decision: Mapped["Decision | None"] = relationship(
        back_populates="corrections", foreign_keys=[decision_id]
    )
    task: Mapped["Task | None"] = relationship(
        back_populates="corrections", foreign_keys=[task_id]
    )


# ── Users ────────────────────────────────────────────────────────────

class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(
        String(20), default="employee"
    )  # employee | manager | leadership | admin
    allowed_groups: Mapped[list] = mapped_column(JSON, default=lambda: ["all"])
    avatar_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
