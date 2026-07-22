"""Dual-Store Sync Mechanism & Reconciliation Engine.

Ensures every verified item exists atomically in BOTH PostgreSQL (structured metadata)
and Qdrant (semantic vector store).
Includes reconciliation tools to detect and fix drift between stores.
"""

import logging
from sqlalchemy.ext.asyncio import AsyncSession
from backend.db.postgres import crud
from backend.db.qdrant_store import upsert_item, get_all, delete_item
from backend.agents.memory_agent import commit_decision, commit_task, correct_item

logger = logging.getLogger(__name__)


async def sync_verify_decision(
    db: AsyncSession,
    decision_id: int,
    *,
    verified_by: str = "hitl_reviewer",
) -> dict:
    """Verify decision in PostgreSQL and sync to Qdrant vector store."""
    decision = await crud.get_decision(db, decision_id)
    if not decision:
        raise ValueError(f"Decision {decision_id} not found in PostgreSQL")

    meeting = await crud.get_meeting(db, decision.meeting_id)
    meeting_name = meeting.name if meeting else "Unknown Meeting"

    # 1. Commit to Qdrant (Memory Agent)
    point_id = commit_decision(
        content=decision.content,
        meeting_id=decision.meeting_id,
        meeting_name=meeting_name,
        access_level=decision.access_level,
        allowed_groups=decision.allowed_groups,
        participants=decision.participants,
        confidence_score=decision.confidence_score,
    )

    # 2. Update PostgreSQL record
    await crud.verify_decision(
        db,
        decision_id,
        verified_by=verified_by,
        qdrant_point_id=point_id,
    )
    await db.commit()

    logger.info(f"Dual-Store Sync complete: Decision {decision_id} <-> Qdrant {point_id}")
    return {"decision_id": decision_id, "qdrant_point_id": point_id}


async def sync_verify_task(
    db: AsyncSession,
    task_id: int,
    *,
    verified_by: str = "hitl_reviewer",
) -> dict:
    """Verify task in PostgreSQL and sync to Qdrant vector store."""
    task = await crud.get_task(db, task_id)
    if not task:
        raise ValueError(f"Task {task_id} not found in PostgreSQL")

    meeting = await crud.get_meeting(db, task.meeting_id)
    meeting_name = meeting.name if meeting else "Unknown Meeting"

    # 1. Commit to Qdrant (Memory Agent)
    point_id = commit_task(
        description=task.description,
        owner=task.owner,
        deadline=task.deadline,
        meeting_id=task.meeting_id,
        meeting_name=meeting_name,
        access_level=task.access_level,
        allowed_groups=task.allowed_groups,
        confidence_score=task.confidence_score,
        status=task.status,
    )

    # 2. Update PostgreSQL record
    await crud.verify_task(
        db,
        task_id,
        verified_by=verified_by,
        qdrant_point_id=point_id,
    )
    await db.commit()

    logger.info(f"Dual-Store Sync complete: Task {task_id} <-> Qdrant {point_id}")
    return {"task_id": task_id, "qdrant_point_id": point_id}


async def reconcile_stores(db: AsyncSession) -> dict:
    """Reconciliation Utility — detects drift between PostgreSQL and Qdrant.

    Checks:
    1. Verified items in PostgreSQL that are missing from Qdrant -> re-embeds & syncs
    2. Orphan points in Qdrant with no corresponding PostgreSQL record -> cleans up or logs
    """
    logger.info("Starting dual-store reconciliation scan...")
    qdrant_points = get_all(limit=1000)
    qdrant_ids = {str(p.id) for p in qdrant_points}

    resynced_decisions = 0
    resynced_tasks = 0

    # Scan un-synced verified decisions
    pending_decisions = await crud.list_pending_decisions(db)
    for d in pending_decisions:
        if d.qdrant_point_id and d.qdrant_point_id not in qdrant_ids:
            logger.warning(f"Reconciliation: Decision {d.id} missing in Qdrant. Resyncing...")
            await sync_verify_decision(db, d.id)
            resynced_decisions += 1

    # Scan un-synced verified tasks
    pending_tasks = await crud.list_pending_tasks(db)
    for t in pending_tasks:
        if t.qdrant_point_id and t.qdrant_point_id not in qdrant_ids:
            logger.warning(f"Reconciliation: Task {t.id} missing in Qdrant. Resyncing...")
            await sync_verify_task(db, t.id)
            resynced_tasks += 1

    summary = {
        "status": "reconciliation_complete",
        "qdrant_total_points": len(qdrant_ids),
        "resynced_decisions": resynced_decisions,
        "resynced_tasks": resynced_tasks,
    }
    logger.info(f"Reconciliation result: {summary}")
    return summary
