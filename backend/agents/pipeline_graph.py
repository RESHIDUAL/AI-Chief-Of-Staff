"""LangGraph State Machine for the AI Chief of Staff meeting processing pipeline.

Defines the agentic workflow graph:
  [Ingest Transcript]
         │
         ▼
  [Extraction Agent]  ── (Extracts Decisions & Tasks with Confidence Scores)
         │
         ▼
 [Score & Route Node] ──► [HITL Review Queue] ──► [Memory Agent]

No extraction is embedded until an authorized reviewer explicitly approves it.
"""

import logging
from typing import TypedDict, List, Dict, Any, Optional
from datetime import datetime, timezone

from backend.agents.extraction_agent import extract_from_transcript
from backend.observability.tracing import traced_node

logger = logging.getLogger(__name__)

# ── State Definition ───────────────────────────────────────────────────

class MeetingState(TypedDict):
    meeting_id: str
    meeting_name: str
    transcript: str
    default_access_level: str
    status: str
    decisions: List[Dict[str, Any]]
    tasks: List[Dict[str, Any]]
    auto_approved_decisions: List[Dict[str, Any]]
    auto_approved_tasks: List[Dict[str, Any]]
    pending_review_decisions: List[Dict[str, Any]]
    pending_review_tasks: List[Dict[str, Any]]
    error: Optional[str]
    current_step: str
    created_at: str
    updated_at: str


# ── Graph Nodes ────────────────────────────────────────────────────────

@traced_node("extract")
def node_extract(state: MeetingState) -> MeetingState:
    """Node 1: Call Extraction Agent to extract decisions and tasks with confidence scores."""
    logger.info(f"[Graph Node: Extract] Processing meeting {state['meeting_id']}")
    state["current_step"] = "extracting"
    state["updated_at"] = datetime.now(timezone.utc).isoformat()

    try:
        data = extract_from_transcript(state["transcript"], state["meeting_id"])
        state["decisions"] = data.get("decisions", [])
        state["tasks"] = data.get("tasks", [])
        if data.get("_raw_error"):
            state["error"] = data["_raw_error"]
        state["status"] = "extracted"
    except Exception as e:
        logger.error(f"[Graph Node: Extract] Error: {e}")
        state["error"] = str(e)
        state["status"] = "failed"

    return state


@traced_node("score_and_route")
def node_score_and_route(state: MeetingState) -> MeetingState:
    """Node 2: Evaluate confidence scores and split items into auto-approve vs pending review."""
    logger.info(f"[Graph Node: Score & Route] Evaluating confidence scores for {state['meeting_id']}")
    state["current_step"] = "routing"

    AUTO_APPROVE_THRESHOLD = 0.90

    auto_decisions = []
    pending_decisions = []
    for d in state["decisions"]:
        score = float(d.get("confidence_score", 0.0))
        if score >= AUTO_APPROVE_THRESHOLD:
            d["auto_approved"] = True
            auto_decisions.append(d)
        else:
            d["auto_approved"] = False
            pending_decisions.append(d)

    auto_tasks = []
    pending_tasks = []
    for t in state["tasks"]:
        score = float(t.get("confidence_score", 0.0))
        if score >= AUTO_APPROVE_THRESHOLD:
            t["auto_approved"] = True
            auto_tasks.append(t)
        else:
            t["auto_approved"] = False
            pending_tasks.append(t)

    state["auto_approved_decisions"] = auto_decisions
    state["auto_approved_tasks"] = auto_tasks
    state["pending_review_decisions"] = pending_decisions
    state["pending_review_tasks"] = pending_tasks

    logger.info(
        f"[Graph Node: Score & Route] {len(auto_decisions)} decisions & {len(auto_tasks)} tasks "
        f"auto-approved. {len(pending_decisions)} decisions & {len(pending_tasks)} tasks routed to HITL review."
    )
    return state


@traced_node("auto_embed")
def node_auto_embed(state: MeetingState) -> MeetingState:
    """Node 3: retain every extraction for human review; never auto-commit memory."""
    logger.info(f"[Graph Node: HITL Queue] Queueing extracted items for {state['meeting_id']}")
    state["current_step"] = "awaiting_human_review"
    state["auto_approved_decisions"] = []
    state["auto_approved_tasks"] = []
    state["pending_review_decisions"] = list(state["decisions"])
    state["pending_review_tasks"] = list(state["tasks"])
    state["status"] = "reviewing"

    state["updated_at"] = datetime.now(timezone.utc).isoformat()
    return state


# ── Pipeline Runner ────────────────────────────────────────────────────

def run_agentic_pipeline(
    meeting_id: str,
    meeting_name: str,
    transcript: str,
    default_access_level: str = "general",
) -> MeetingState:
    """Execute the full agentic orchestration pipeline."""
    initial_state: MeetingState = {
        "meeting_id": meeting_id,
        "meeting_name": meeting_name,
        "transcript": transcript,
        "default_access_level": default_access_level,
        "status": "received",
        "decisions": [],
        "tasks": [],
        "auto_approved_decisions": [],
        "auto_approved_tasks": [],
        "pending_review_decisions": [],
        "pending_review_tasks": [],
        "error": None,
        "current_step": "init",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "updated_at": datetime.now(timezone.utc).isoformat(),
    }

    # Step 1: Extraction
    state = node_extract(initial_state)

    if state["status"] == "failed":
        return state

    # Step 2: Score & Route
    state = node_score_and_route(state)

    # Step 3: Auto Embed high confidence items
    state = node_auto_embed(state)

    return state
