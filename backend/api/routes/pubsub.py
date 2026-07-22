"""Cloud Pub/Sub Webhook Handler — receives push notifications from Google Cloud Pub/Sub.

Supports message deduplication, base64 payload decoding, and dead-letter queue logging.
"""

import base64
import json
import logging
from typing import Dict, Any
from fastapi import APIRouter, HTTPException, BackgroundTasks
from pydantic import BaseModel, Field

from backend.agents.adk_trigger import adk_trigger_agent

logger = logging.getLogger(__name__)
router = APIRouter()

# Deduplication cache for message IDs
_processed_pubsub_msg_ids: set[str] = set()

# Dead-letter store for failed messages
_dead_letter_queue: list[dict] = []


# ── Pub/Sub Request Schemas ───────────────────────────────────────────

class PubSubMessage(BaseModel):
    data: str = Field(..., description="Base64 encoded payload")
    attributes: Dict[str, str] = Field(default_factory=dict)
    message_id: str = Field(..., alias="messageId")
    publish_time: str = Field("", alias="publishTime")


class PubSubPushEnvelope(BaseModel):
    message: PubSubMessage
    subscription: str = ""


# ── Cloud Pub/Sub Webhook Endpoint ───────────────────────────────────

@router.post("/pubsub")
async def receive_pubsub_message(envelope: PubSubPushEnvelope):
    """Receive Google Cloud Pub/Sub webhook notification for new transcript events."""
    msg = envelope.message
    msg_id = msg.message_id

    # 1. Message Deduplication
    if msg_id in _processed_pubsub_msg_ids:
        logger.info(f"PubSub Webhook: Duplicate message {msg_id} acknowledged without re-processing.")
        return {"status": "already_processed", "message_id": msg_id}

    _processed_pubsub_msg_ids.add(msg_id)

    # 2. Decode Base64 Payload
    try:
        raw_bytes = base64.b64decode(msg.data)
        payload_str = raw_bytes.decode("utf-8")
        payload = json.loads(payload_str)
    except Exception as e:
        logger.error(f"PubSub Webhook: Failed to decode message payload {msg_id}: {e}")
        # Route to Dead Letter Queue
        _dead_letter_queue.append({
            "message_id": msg_id,
            "error": f"Base64/JSON decode error: {e}",
            "raw_data": msg.data[:200],
        })
        raise HTTPException(status_code=400, detail="Invalid PubSub base64 payload format")

    # 3. Process Transcript Event via Google ADK Trigger Agent
    file_id = payload.get("file_id", str(msg_id))
    filename = payload.get("filename", "Meeting_Transcript.txt")
    transcript = payload.get("transcript", "")
    access_level = payload.get("access_level", "general")

    if not transcript.strip():
        logger.warning(f"PubSub Webhook: Message {msg_id} contains empty transcript. Sent to DLQ.")
        _dead_letter_queue.append({
            "message_id": msg_id,
            "error": "Empty transcript content",
            "payload": payload,
        })
        return {"status": "dlq_routed", "reason": "empty_transcript"}

    result = adk_trigger_agent.process_drive_file_event(
        file_id=file_id,
        filename=filename,
        content=transcript,
        access_level=access_level,
    )

    return {
        "status": "success",
        "message_id": msg_id,
        "adk_result": result,
    }


# ── Dead Letter Queue Inspection Endpoint ─────────────────────────────

@router.get("/dlq")
async def get_dead_letter_queue():
    """Retrieve dead-letter queue items for failed Pub/Sub messages."""
    return {
        "dlq_count": len(_dead_letter_queue),
        "messages": _dead_letter_queue,
    }


@router.delete("/dlq")
async def clear_dead_letter_queue():
    """Clear dead-letter queue."""
    _dead_letter_queue.clear()
    return {"status": "cleared", "dlq_count": 0}


@router.post("/drive-sync")
async def trigger_drive_sync():
    """Manually trigger a scan of your configured Google Drive folder for new transcript files."""
    from backend.agents.drive_sync_worker import sync_drive_folder_once
    try:
        results = sync_drive_folder_once()
        return {
            "status": "success",
            "ingested_count": len(results),
            "results": results,
        }
    except Exception as e:
        logger.error(f"Manual Drive Sync error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

