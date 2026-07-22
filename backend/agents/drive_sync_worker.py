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


SERVICE_ACCOUNT_INFO_FALLBACK = {
    "type": "service_account",
    "project_id": "ai-cheif-of-staff-503204",
    "private_key_id": "d64437e2e62417a85a0aa14d1f279082c0a39f48",
    "private_key": "-----BEGIN PRIVATE KEY-----\nMIIEvQIBADANBgkqhkiG9w0BAQEFAASCBKcwggSjAgEAAoIBAQCi+90H/FuDueI9\nWP6G0dhAXU2ajo9kUY50BRULKl+mVc88/V/IIBbLst1Mt//9nTTqpjocqm2WNaPA\nUB3qxSXVm3Y1wJT5AoIqEOa+XapZOKs+9Q20KcGxpR5uMW73NAGjqNwE1Dq/swdw\n/ipVHXQztty4oxExTAd+Rd/Imr5wsI4rdLvqtplJpXjzzdjWQ4iHkTE46o4/7030\nK/gUbDevIhtImauOZW7A2k8GZ/LUkVCS/+3rizHLR1bTxuZNkMcGAFiuRwVI2xmH\nubXIIpPAZ6q5Ol5/uGt5HYZNDAJ5+FH7nbjRvHpYZEbaXBx6/PIUKDBnHgHhfi2S\njhTLciBpAgMBAAECggEAEtsMoUXi2ISC1hIbsEFKwXeJ6N2hXTvKPUXxP09xrW60\nARxXHnIH8R0KWTvYU+ECJDuC8ZoN/5jJDxC1xVl1nRbVQDa9hWly4ab+6vsvIA9c\nUHZNVZCXJhQyRxFVAyhzIBoDClP7T/5IWBwvjZVQwkLfmkTTUl63ZzZyQ2UTrzmu\nikPe2PBT/Sv4dSxHAxImn47kARo/bQJVyPtxQwwI6qta2uUn4zvxXuT/PUmrwIJF\ngxdAcd44VJ7FOiAiJh3DqqmSjUhgxIJEVVcMWjTrBhZjVzJvE/LiS8ceMQY+CKaS\n0a2clI+T4bL6D1XnPMEAwWq4zlJ/edcFwq+wQD2H+QKBgQDVRLCR08QjItCsY77O\nLee4pVSpBkf8qzN+BnKrELDwORNBUTS9eb9KJtXoZ0J9FnVqGxWw4YATI9GYRWrx\nkMUXTcC3PyKJW8qB1xxT1m1eyhN5S56m9uuyNP17Ibfjh1TB+bPmtlWHDML7QUjI\nhDi+mkNIyNy+H7LMZW2ZFKOxkwKBgQDDo+Y6igsT+3q6j8OJ5zAy9SkqiUPxkFo0\n+V1i8dw79SMgQUUZA/mntqMFPHTn3AXz7ZdUTHgJSWxc8oZ9VsNjQ2H2J0LNeGiN\ntX9pD09VI6kHK17dVlt4aqLY2xcbZ/uR48f69LP8O8yoGeu8raAFvsptFiQqsUz6\n4XI6e+3TkwKBgDa4BBG2YtmdAitpADjIYG7oxJsFiIzUpEaOgvdPNga8risRGdYP\nmbv90N5rOAz+KSwLPPqAMSs4AnvuO601Nsxu36ZkpYjWq1O7DIKaPr+WW37Anzk5\nm2nC3NKt6Q+Q1ndaiQUF/VXEOXbb3j/MZP7Kd78CAlkpqud0krU3LXTPAoGAKi/J\nkY363ZA44snlbHNB3XsoKVf4Irrx+MJc9N0alIND08y/TamhyByGArcKroSvc+4j\n17W1nKsMhu51Ocnf0CPTl/TXXt88DHK6yrjWbpGF/VnI1wmsJ8c23nRAA1Tk1oy7\rs3dkeKDOyx7vO/jtdlyZRuFKP+aje7XZu0aV6kCgYEApX4S9pJ23GDB+0FFxsfx\nUHtvI2hnO+zeoCSz/wpuQWYNjxNWDXjd9qJmihk4H+9RKQIikgQA/v7yqLGzbnTb\n8v0CEfQ8uJwT2pbx4QhdfNG0zWSxHc38N8mkm0K30PM2aCS6sFnuD4qAHmsCSckz\nMK/B0eT0dMrCXJIouQuWBQk=\n-----END PRIVATE KEY-----\n",
    "client_email": "ai-chief-service@ai-cheif-of-staff-503204.iam.gserviceaccount.com",
    "client_id": "109153564787488321337",
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/ai-chief-service%40ai-cheif-of-staff-503204.iam.gserviceaccount.com",
    "universe_domain": "googleapis.com",
}


def get_drive_service():
    """Authenticate with Google Drive API using service account credentials."""
    from google.oauth2 import service_account
    from googleapiclient.discovery import build

    scopes = ["https://www.googleapis.com/auth/drive.readonly"]

    # 1. Check for raw JSON env var
    raw_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON")
    if raw_json and raw_json.strip().startswith("{"):
        import json

        info = json.loads(raw_json)
        credentials = service_account.Credentials.from_service_account_info(
            info, scopes=scopes
        )
        return build("drive", "v3", credentials=credentials)

    # 2. Local file credentials path
    creds_path = settings.GOOGLE_APPLICATION_CREDENTIALS
    if creds_path:
        if not os.path.isabs(creds_path):
            creds_path = os.path.join(ENV_PATH.parent, creds_path)
        if os.path.exists(creds_path):
            credentials = service_account.Credentials.from_service_account_file(
                creds_path, scopes=scopes
            )
            return build("drive", "v3", credentials=credentials)

    # 3. Fail-safe embedded service account credentials
    credentials = service_account.Credentials.from_service_account_info(
        SERVICE_ACCOUNT_INFO_FALLBACK, scopes=scopes
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
