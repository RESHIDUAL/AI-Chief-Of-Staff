"""Google Drive Sync Worker — monitors Google Drive folder for text transcripts and automatically ingests them.

Uses service account credentials from settings.GOOGLE_APPLICATION_CREDENTIALS and
folder ID from settings.GOOGLE_DRIVE_FOLDER_ID.
"""

import os
import time
import logging
from typing import List, Dict, Any

from backend.config.settings import settings, ENV_PATH
from backend.agents.adk_trigger import adk_trigger_agent

logger = logging.getLogger(__name__)

# Track processed files locally so we don't re-ingest
_processed_file_ids: set[str] = set()


def get_drive_service():
    """Authenticate with Google Drive API using service account credentials."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    # 1. Check for raw JSON env var (for cloud deployments like Render)
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json and raw_json.strip().startswith("{"):
        import json
        info = json.loads(raw_json)
        credentials = service_account.Credentials.from_service_account_info(info, scopes=scopes)
        return build("drive", "v3", credentials=credentials)

    # 2. Local file credentials path fallback
    creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if not os.path.isabs(creds_path):
        creds_path = os.path.join(ENV_PATH.parent, creds_path)

    if not os.path.exists(creds_path):
        raise FileNotFoundError(f"Service account credential file not found at: {creds_path}")

    credentials = service_account.Credentials.from_service_account_file(
        creds_path, scopes=scopes
    )
    return build("drive", "v3", credentials=credentials)


def sync_drive_folder_once(force: bool = True) -> List[Dict[str, Any]]:
    """Fetch all new files in the configured Google Drive folder and trigger ingestion."""
    folder_id = settings.GOOGLE_DRIVE_FOLDER_ID
    if not folder_id:
        logger.warning("GOOGLE_DRIVE_FOLDER_ID is not configured in .env")
        return []

    if force:
        _processed_file_ids.clear()

    try:
        service = get_drive_service()
        # Query files inside the folder
        query = f"'{folder_id}' in parents and trashed = false"
        results = service.files().list(
            q=query,
            fields="files(id, name, mimeType, createdTime)",
            pageSize=50
        ).execute()

        files = results.get("files", [])
        ingested_results = []

        for f in files:
            file_id = f["id"]
            filename = f["name"]

            if file_id in _processed_file_ids:
                continue

            # Read text file content
            try:
                if f.get("mimeType") == "application/vnd.google-apps.document":
                    # Export Google Doc as plain text
                    content_bytes = service.files().export_media(
                        fileId=file_id, mimeType="text/plain"
                    ).execute()
                    content = content_bytes.decode("utf-8", errors="ignore")
                else:
                    # Download binary/text file
                    content_bytes = service.files().get_media(fileId=file_id).execute()
                    content = content_bytes.decode("utf-8", errors="ignore")

                if not content.strip():
                    continue

                logger.info(f"Drive Sync Worker: Found new file '{filename}' ({file_id})")
                res = adk_trigger_agent.process_drive_file_event(
                    file_id=file_id,
                    filename=filename,
                    content=content,
                    access_level="general",
                )
                _processed_file_ids.add(file_id)
                ingested_results.append(res)
            except Exception as e:
                logger.error(f"Drive Sync Worker: Error downloading/processing file '{filename}': {e}")

        return ingested_results

    except Exception as e:
        logger.error(f"Drive Sync Worker: Google Drive API sync failed: {e}")
        return []


def run_continuous_drive_sync(interval_seconds: int = 15):
    """Run continuous background loop polling Google Drive every N seconds."""
    logging.basicConfig(level=logging.INFO)
    logger.info(f"Starting Google Drive Sync Worker (Polling folder '{settings.GOOGLE_DRIVE_FOLDER_ID}' every {interval_seconds}s)...")

    while True:
        try:
            results = sync_drive_folder_once()
            if results:
                logger.info(f"Drive Sync Worker: Successfully ingested {len(results)} new transcript(s).")
        except Exception as e:
            logger.error(f"Drive Sync Worker loop error: {e}")

        time.sleep(interval_seconds)


if __name__ == "__main__":
    run_continuous_drive_sync(interval_seconds=15)
