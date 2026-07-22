"""Ingestion Orchestrator — manages the full pipeline from transcript to committed memory.

Coordinates: receive transcript -> dispatch to Extraction Agent -> score & route ->
auto-approve high confidence items via Memory Agent -> queue remaining for HITL review.
"""

import uuid
import logging
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime, timezone

from backend.agents.pipeline_graph import run_agentic_pipeline

logger = logging.getLogger(__name__)


class PipelineStatus(str, Enum):
    """Status of a meeting processing pipeline."""
    RECEIVED = "received"
    EXTRACTING = "extracting"
    EXTRACTED = "extracted"
    ROUTING = "routing"
    REVIEWING = "reviewing"
    COMMITTED = "committed"
    FAILED = "failed"


@dataclass
class PipelineState:
    """Tracks the state of a single meeting ingestion pipeline."""
    meeting_id: str
    meeting_name: str
    status: PipelineStatus = PipelineStatus.RECEIVED
    transcript: str = ""
    decisions: list = field(default_factory=list)
    tasks: list = field(default_factory=list)
    auto_approved_decisions: list = field(default_factory=list)
    auto_approved_tasks: list = field(default_factory=list)
    pending_review_decisions: list = field(default_factory=list)
    pending_review_tasks: list = field(default_factory=list)
    error: str | None = None
    created_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


# In-memory pipeline state store
_pipelines: dict[str, PipelineState] = {}


def ingest_transcript(
    transcript: str,
    meeting_name: str,
    default_access_level: str = "general",
) -> PipelineState:
    """Start the ingestion pipeline for a new transcript via agentic graph execution."""
    # Deduplication Guardrail: Prevent duplicate ingestion for identical meeting_name or transcript
    clean_name = meeting_name.strip().lower()
    for existing_id, existing in list(_pipelines.items()):
        if existing.meeting_name.strip().lower() == clean_name or (transcript.strip() and existing.transcript.strip() == transcript.strip()):
            logger.info(f"Ingestion Orchestrator: Skipped duplicate ingestion for '{meeting_name}' (Existing ID: {existing_id})")
            return existing

    meeting_id = str(uuid.uuid4())[:8]
    logger.info(f"Ingestion Orchestrator starting pipeline {meeting_id} for '{meeting_name}'")

    graph_state = run_agentic_pipeline(
        meeting_id=meeting_id,
        meeting_name=meeting_name,
        transcript=transcript,
        default_access_level=default_access_level,
    )

    state = PipelineState(
        meeting_id=graph_state["meeting_id"],
        meeting_name=graph_state["meeting_name"],
        status=PipelineStatus(graph_state["status"]),
        transcript=graph_state["transcript"],
        decisions=graph_state["decisions"],
        tasks=graph_state["tasks"],
        auto_approved_decisions=graph_state["auto_approved_decisions"],
        auto_approved_tasks=graph_state["auto_approved_tasks"],
        pending_review_decisions=graph_state["pending_review_decisions"],
        pending_review_tasks=graph_state["pending_review_tasks"],
        error=graph_state["error"],
        created_at=graph_state["created_at"],
        updated_at=graph_state["updated_at"],
    )

    _pipelines[meeting_id] = state
    return state


def get_pipeline(meeting_id: str) -> PipelineState | None:
    """Get a pipeline state by meeting ID."""
    return _pipelines.get(meeting_id)


def list_pipelines() -> list[PipelineState]:
    """List all pipeline states."""
    return list(_pipelines.values())


def delete_pipeline(meeting_id: str) -> bool:
    """Delete a pipeline state by meeting ID."""
    if meeting_id in _pipelines:
        del _pipelines[meeting_id]
        return True
    return False


def update_pipeline_status(meeting_id: str, status: PipelineStatus) -> None:
    """Update the status of a pipeline."""
    state = _pipelines.get(meeting_id)
    if state:
        state.status = status
        state.updated_at = datetime.now(timezone.utc).isoformat()
