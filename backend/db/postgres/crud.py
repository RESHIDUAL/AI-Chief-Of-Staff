"""CRUD operations for the Meeting Metadata DB (PostgreSQL)."""

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.db.postgres.models import Meeting, Decision, Task, Correction, User


# ── Meeting CRUD ─────────────────────────────────────────────────────

async def create_meeting(
    db: AsyncSession,
    *,
    meeting_id: str,
    name: str,
    transcript: str,
    source: str = "manual_paste",
) -> Meeting:
    """Create a new meeting record."""
    meeting = Meeting(id=meeting_id, name=name, transcript=transcript, source=source)
    db.add(meeting)
    await db.flush()
    return meeting


async def get_meeting(db: AsyncSession, meeting_id: str) -> Meeting | None:
    """Get a meeting by ID with its decisions and tasks."""
    stmt = (
        select(Meeting)
        .where(Meeting.id == meeting_id)
        .options(selectinload(Meeting.decisions), selectinload(Meeting.tasks))
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_meetings(db: AsyncSession, limit: int = 50) -> list[Meeting]:
    """List recent meetings."""
    stmt = select(Meeting).order_by(Meeting.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def update_meeting_status(
    db: AsyncSession, meeting_id: str, status: str
) -> None:
    """Update pipeline status for a meeting."""
    stmt = update(Meeting).where(Meeting.id == meeting_id).values(pipeline_status=status)
    await db.execute(stmt)


# ── Decision CRUD ────────────────────────────────────────────────────

async def create_decision(
    db: AsyncSession,
    *,
    meeting_id: str,
    content: str,
    participants: list[str] | None = None,
    access_level: str = "general",
    allowed_groups: list[str] | None = None,
    confidence_score: float = 0.0,
) -> Decision:
    """Create a new decision record."""
    decision = Decision(
        meeting_id=meeting_id,
        content=content,
        participants=participants or [],
        access_level=access_level,
        allowed_groups=allowed_groups or ["all"],
        confidence_score=confidence_score,
    )
    db.add(decision)
    await db.flush()
    return decision


async def get_decision(db: AsyncSession, decision_id: int) -> Decision | None:
    """Get a decision by ID."""
    stmt = select(Decision).where(Decision.id == decision_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_pending_decisions(db: AsyncSession) -> list[Decision]:
    """List all unverified decisions."""
    stmt = (
        select(Decision)
        .where(Decision.verified == False)
        .order_by(Decision.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def verify_decision(
    db: AsyncSession,
    decision_id: int,
    *,
    verified_by: str = "anonymous",
    qdrant_point_id: str | None = None,
    content: str | None = None,
    access_level: str | None = None,
) -> Decision | None:
    """Mark a decision as verified (approved)."""
    decision = await get_decision(db, decision_id)
    if not decision:
        return None
    decision.verified = True
    decision.verified_by = verified_by
    if qdrant_point_id:
        decision.qdrant_point_id = qdrant_point_id
    if content is not None:
        decision.content = content
    if access_level is not None:
        decision.access_level = access_level
    await db.flush()
    return decision


# ── Task CRUD ────────────────────────────────────────────────────────

async def create_task(
    db: AsyncSession,
    *,
    meeting_id: str,
    description: str,
    owner: str = "",
    deadline: str = "",
    status: str = "open",
    access_level: str = "general",
    allowed_groups: list[str] | None = None,
    confidence_score: float = 0.0,
) -> Task:
    """Create a new task record."""
    task = Task(
        meeting_id=meeting_id,
        description=description,
        owner=owner,
        deadline=deadline,
        status=status,
        access_level=access_level,
        allowed_groups=allowed_groups or ["all"],
        confidence_score=confidence_score,
    )
    db.add(task)
    await db.flush()
    return task


async def get_task(db: AsyncSession, task_id: int) -> Task | None:
    """Get a task by ID."""
    stmt = select(Task).where(Task.id == task_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_pending_tasks(db: AsyncSession) -> list[Task]:
    """List all unverified tasks."""
    stmt = (
        select(Task)
        .where(Task.verified == False)
        .order_by(Task.created_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def verify_task(
    db: AsyncSession,
    task_id: int,
    *,
    verified_by: str = "anonymous",
    qdrant_point_id: str | None = None,
    description: str | None = None,
    owner: str | None = None,
    deadline: str | None = None,
    access_level: str | None = None,
) -> Task | None:
    """Mark a task as verified (approved)."""
    task = await get_task(db, task_id)
    if not task:
        return None
    task.verified = True
    task.verified_by = verified_by
    if qdrant_point_id:
        task.qdrant_point_id = qdrant_point_id
    if description is not None:
        task.description = description
    if owner is not None:
        task.owner = owner
    if deadline is not None:
        task.deadline = deadline
    if access_level is not None:
        task.access_level = access_level
    await db.flush()
    return task


async def update_task_status(
    db: AsyncSession, task_id: int, status: str
) -> Task | None:
    """Update task status (open/in_progress/done)."""
    task = await get_task(db, task_id)
    if not task:
        return None
    task.status = status
    await db.flush()
    return task


# ── Correction CRUD ──────────────────────────────────────────────────

async def create_correction(
    db: AsyncSession,
    *,
    item_type: str,
    decision_id: int | None = None,
    task_id: int | None = None,
    old_content: str,
    new_content: str,
    corrected_by: str = "anonymous",
) -> Correction:
    """Log a correction to the audit trail."""
    correction = Correction(
        item_type=item_type,
        decision_id=decision_id,
        task_id=task_id,
        old_content=old_content,
        new_content=new_content,
        corrected_by=corrected_by,
    )
    db.add(correction)
    await db.flush()
    return correction


async def list_corrections_for_decision(
    db: AsyncSession, decision_id: int
) -> list[Correction]:
    """Get correction history for a decision."""
    stmt = (
        select(Correction)
        .where(Correction.decision_id == decision_id)
        .order_by(Correction.corrected_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def list_corrections_for_task(
    db: AsyncSession, task_id: int
) -> list[Correction]:
    """Get correction history for a task."""
    stmt = (
        select(Correction)
        .where(Correction.task_id == task_id)
        .order_by(Correction.corrected_at.desc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


# ── User CRUD ────────────────────────────────────────────────────────

async def get_or_create_user(
    db: AsyncSession,
    *,
    email: str,
    name: str,
    role: str = "employee",
    allowed_groups: list[str] | None = None,
) -> User:
    """Get a user by email, or create one if they don't exist."""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()
    if user:
        return user
    user = User(
        email=email,
        name=name,
        role=role,
        allowed_groups=allowed_groups or ["all"],
    )
    db.add(user)
    await db.flush()
    return user


async def get_user_by_email(db: AsyncSession, email: str) -> User | None:
    """Get a user by email."""
    stmt = select(User).where(User.email == email)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ── Stats ────────────────────────────────────────────────────────────

async def get_dashboard_stats(db: AsyncSession) -> dict:
    """Get summary stats for the dashboard."""
    from sqlalchemy import func

    total_decisions = await db.scalar(select(func.count(Decision.id)))
    total_tasks = await db.scalar(select(func.count(Task.id)))
    pending_decisions = await db.scalar(
        select(func.count(Decision.id)).where(Decision.verified == False)
    )
    pending_tasks = await db.scalar(
        select(func.count(Task.id)).where(Task.verified == False)
    )
    open_tasks = await db.scalar(
        select(func.count(Task.id)).where(Task.status == "open")
    )
    total_meetings = await db.scalar(select(func.count(Meeting.id)))

    return {
        "total_decisions": total_decisions or 0,
        "total_tasks": total_tasks or 0,
        "pending_decisions": pending_decisions or 0,
        "pending_tasks": pending_tasks or 0,
        "open_tasks": open_tasks or 0,
        "total_meetings": total_meetings or 0,
    }
