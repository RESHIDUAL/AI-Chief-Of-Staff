"""Ingestion API routes — receive transcripts and trigger the extraction pipeline."""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.models.schemas import TranscriptIngestRequest, ExtractionResponse, DecisionOut, TaskOut
from backend.agents.ingestion_orchestrator import ingest_transcript, get_pipeline, list_pipelines
from backend.db.postgres.database import get_db
from backend.db.postgres import crud

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/transcript", response_model=ExtractionResponse)
async def ingest_transcript_endpoint(
    req: TranscriptIngestRequest,
    db: AsyncSession = Depends(get_db),
):
    """Ingest a raw meeting transcript and extract decisions & tasks.

    1. Dispatches to the Agentic Extraction Pipeline (Lyzr Agent)
    2. Safely persists meeting and extracted items to PostgreSQL if available
    3. Returns structured results for HITL review
    """
    MAX_TRANSCRIPT_LENGTH = 100_000  # ~25k tokens, reject anything larger
    if len(req.transcript) > MAX_TRANSCRIPT_LENGTH:
        raise HTTPException(
            status_code=413,
            detail=f"Transcript exceeds maximum length of {MAX_TRANSCRIPT_LENGTH:,} characters. Please split into smaller segments."
        )
        
    logger.info(f"Ingesting transcript for meeting: {req.meeting_name}")

    # Run agentic extraction pipeline
    state = ingest_transcript(
        transcript=req.transcript,
        meeting_name=req.meeting_name,
        default_access_level=req.default_access_level.value,
    )

    if state.status.value == "failed":
        raise HTTPException(status_code=500, detail=f"Extraction failed: {state.error}")

    # Persist meeting & extracted items to PostgreSQL if database connection is active
    try:
        meeting = await crud.create_meeting(
            db,
            meeting_id=state.meeting_id,
            name=state.meeting_name,
            transcript=req.transcript,
            source="manual_paste",
        )
        await crud.update_meeting_status(db, state.meeting_id, "extracted")

        for d in state.decisions:
            await crud.create_decision(
                db,
                meeting_id=state.meeting_id,
                content=d.get("content", ""),
                participants=d.get("participants", []),
                access_level=d.get("access_level", req.default_access_level.value),
                confidence_score=d.get("confidence_score", 0.0),
            )

        for t in state.tasks:
            await crud.create_task(
                db,
                meeting_id=state.meeting_id,
                description=t.get("description", ""),
                owner=t.get("owner", ""),
                deadline=t.get("deadline", ""),
                status=t.get("status", "open"),
                access_level=req.default_access_level.value,
                confidence_score=t.get("confidence_score", 0.0),
            )

        await db.commit()
        logger.info(f"Meeting {state.meeting_id} persisted to PostgreSQL successfully.")
    except Exception as e:
        logger.warning(
            f"PostgreSQL persistence skipped for {state.meeting_id} ({e}). "
            "Pipeline results remain fully available in memory state."
        )

    return ExtractionResponse(
        meeting_id=state.meeting_id,
        meeting_name=state.meeting_name,
        status=state.status.value,
        decisions=[
            DecisionOut(
                content=d.get("content", ""),
                participants=d.get("participants", []),
                access_level=d.get("access_level", "general"),
                confidence_score=d.get("confidence_score", 0.0),
            )
            for d in state.decisions
        ],
        tasks=[
            TaskOut(
                description=t.get("description", ""),
                owner=t.get("owner", ""),
                deadline=t.get("deadline", ""),
                status=t.get("status", "open"),
                confidence_score=t.get("confidence_score", 0.0),
            )
            for t in state.tasks
        ],
        error=state.error,
    )


@router.post("/webhook")
async def ingest_webhook(payload: dict):
    """Receive Pub/Sub events from Google Workspace."""
    logger.info(f"Webhook received: {payload}")
    return {
        "status": "received",
        "message": "Webhook processing active. Use POST /transcript for direct ingest.",
    }


@router.get("/pipeline/{meeting_id}")
async def get_pipeline_status(meeting_id: str):
    """Check the processing status of a meeting pipeline."""
    state = get_pipeline(meeting_id)
    if not state:
        raise HTTPException(status_code=404, detail="Pipeline not found")
    return {
        "meeting_id": state.meeting_id,
        "meeting_name": state.meeting_name,
        "status": state.status.value,
        "decisions_count": len(state.decisions),
        "tasks_count": len(state.tasks),
        "error": state.error,
        "created_at": state.created_at,
        "updated_at": state.updated_at,
    }


@router.get("/pipelines")
async def list_all_pipelines():
    """List all pipeline states."""
    pipelines = list_pipelines()
    return [
        {
            "meeting_id": p.meeting_id,
            "meeting_name": p.meeting_name,
            "status": p.status.value,
            "decisions_count": len(p.decisions),
            "tasks_count": len(p.tasks),
            "created_at": p.created_at,
        }
        for p in pipelines
    ]


@router.get("/meetings")
async def list_meetings(db: AsyncSession = Depends(get_db)):
    """List all meetings from PostgreSQL or memory store."""
    try:
        meetings = await crud.list_meetings(db)
        return [
            {
                "id": m.id,
                "name": m.name,
                "source": m.source,
                "pipeline_status": m.pipeline_status,
                "created_at": m.created_at.isoformat() if m.created_at else None,
            }
            for m in meetings
        ]
    except Exception as e:
        logger.warning(f"PostgreSQL read skipped: {e}")
        # Fallback to pipeline list
        pipelines = list_pipelines()
        return [
            {
                "id": p.meeting_id,
                "name": p.meeting_name,
                "source": "memory",
                "pipeline_status": p.status.value,
                "created_at": p.created_at,
            }
            for p in pipelines
        ]
