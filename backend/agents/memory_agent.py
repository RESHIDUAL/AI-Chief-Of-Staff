"""Memory Agent — owns all embedding and Qdrant operations.

Handles the Correction Feedback Loop: when a human edits a committed item,
this agent re-embeds the content and updates both Qdrant and PostgreSQL.
"""

from datetime import datetime, timezone
from backend.db.embeddings import embed_text
from backend.db.qdrant_store import upsert_item, delete_item


def commit_decision(
    content: str,
    meeting_id: str,
    meeting_name: str,
    access_level: str = "general",
    allowed_groups: list[str] | None = None,
    participants: list[str] | None = None,
    confidence_score: float = 0.0,
    point_id: str | None = None,
) -> str:
    """Embed and commit a decision to Qdrant."""
    vector = embed_text(content)
    payload = {
        "type": "decision",
        "content": content,
        "meeting_id": meeting_id,
        "meeting_name": meeting_name,
        "access_level": access_level,
        "allowed_groups": allowed_groups or ["all"],
        "participants": participants or [],
        "confidence_score": confidence_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verified": True,
        "corrected": False,
    }
    return upsert_item(vector, payload, point_id=point_id)


def commit_task(
    description: str,
    owner: str,
    deadline: str,
    meeting_id: str,
    meeting_name: str,
    access_level: str = "general",
    allowed_groups: list[str] | None = None,
    confidence_score: float = 0.0,
    status: str = "open",
    point_id: str | None = None,
) -> str:
    """Embed and commit a task to Qdrant."""
    content = f"Task: {description}. Owner: {owner}. Deadline: {deadline}."
    vector = embed_text(content)
    payload = {
        "type": "task",
        "content": content,
        "description": description,
        "owner": owner,
        "deadline": deadline,
        "status": status,
        "meeting_id": meeting_id,
        "meeting_name": meeting_name,
        "access_level": access_level,
        "allowed_groups": allowed_groups or ["all"],
        "confidence_score": confidence_score,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "verified": True,
        "corrected": False,
    }
    return upsert_item(vector, payload, point_id=point_id)


def correct_item(
    point_id: str,
    new_content: str,
    existing_payload: dict,
) -> str:
    """Re-embed and update a committed item — the Correction Feedback Loop."""
    vector = embed_text(new_content)
    existing_payload["content"] = new_content
    existing_payload["corrected"] = True
    existing_payload["correction_timestamp"] = datetime.now(timezone.utc).isoformat()
    return upsert_item(vector, existing_payload, point_id=point_id)


def remove_item(point_id: str) -> None:
    """Remove an item from organizational memory."""
    delete_item(point_id)
