"""Google ADK Trigger Agent — monitors Google Drive/Meet for transcript events and triggers ingestion.

Acts as Layer 1 (Ingestion Layer) in the system architecture.
Supports both real-time Google Workspace push triggers and background interval polling.
"""

import os
import re
import uuid
import logging
from datetime import datetime, timezone
from typing import Dict, Any, Optional

from backend.agents.ingestion_orchestrator import ingest_transcript

logger = logging.getLogger(__name__)


# ── Metadata Parser Helper ─────────────────────────────────────────────

def parse_meeting_metadata_from_filename(filename: str) -> Dict[str, str]:
    """Parse meeting title and date from typical Google Meet / Drive transcript filenames.

    Examples:
      - "Transcript - Q3 Product Strategy Standup (2026-07-21).txt" -> Title: Q3 Product Strategy Standup
      - "2026_07_21_Leadership_Sync_Transcript.docx" -> Title: Leadership Sync
    """
    clean_name = os.path.splitext(filename)[0]
    clean_name = re.sub(r"^(transcript\s*-\s*|meeting\s*-\s*)", "", clean_name, flags=re.IGNORECASE)
    clean_name = re.sub(r"(_transcript|-transcript)", "", clean_name, flags=re.IGNORECASE)

    # Extract date if present
    date_match = re.search(r"(\d{4}[-/._]\d{2}[-/._]\d{2})", clean_name)
    meeting_date = date_match.group(1) if date_match else datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Clean title
    title = re.sub(r"\(?\d{4}[-/._]\d{2}[-/._]\d{2}\)?", "", clean_name).strip(" -_")
    title = title if title else "Google Meet Session"

    return {
        "meeting_name": title,
        "date": meeting_date,
        "raw_filename": filename,
    }


# ── Google ADK Trigger Processor ───────────────────────────────────────

class GoogleADKTriggerAgent:
    """Agent monitoring Google Workspace (Drive/Meet) for transcript files."""

    def __init__(self):
        self.processed_file_ids: set[str] = set()

    def process_drive_file_event(
        self,
        file_id: str,
        filename: str,
        content: str,
        access_level: str = "general",
    ) -> Dict[str, Any]:
        """Triggered when Google ADK detects a new meeting transcript landing in Google Drive."""
        if file_id in self.processed_file_ids:
            logger.info(f"ADK Trigger: Duplicate event ignored for file {file_id}")
            return {"status": "duplicate_skipped", "file_id": file_id}

        self.processed_file_ids.add(file_id)

        # 1. Parse metadata
        meta = parse_meeting_metadata_from_filename(filename)
        meeting_name = meta["meeting_name"]

        logger.info(
            f"Google ADK Trigger: Processing transcript '{filename}' "
            f"-> Meeting: '{meeting_name}' (ID: {file_id})"
        )

        # 2. Hand-off to Ingestion Orchestrator Agent (Layer 2)
        pipeline_state = ingest_transcript(
            transcript=content,
            meeting_name=meeting_name,
            default_access_level=access_level,
        )

        return {
            "status": "ingested",
            "file_id": file_id,
            "meeting_id": pipeline_state.meeting_id,
            "meeting_name": meeting_name,
            "pipeline_status": pipeline_state.status.value,
        }


# Singleton trigger instance
adk_trigger_agent = GoogleADKTriggerAgent()
