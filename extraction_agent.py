import json
import re
from lyzr_python_sdk import LyzrAgentAPI
from config import LYZR_API_KEY, EXTRACTION_AGENT_ID

_client = None


def get_client():
    global _client
    if _client is None:
        _client = LyzrAgentAPI(api_key=LYZR_API_KEY)
    return _client


# Paste this as the system prompt of your "Extraction Agent" in Lyzr Studio.
EXTRACTION_SYSTEM_PROMPT = """You are a meeting intelligence extraction agent.
Read the transcript and separate it into two distinct streams: Decisions and Tasks.
A Decision is a conclusion or direction the group committed to (the "why").
A Task is an action item with an owner and ideally a deadline (the "who/what/when").
Do not merge them. Do not include small talk or clarifying questions.

Return ONLY valid JSON, no markdown fences, no commentary, in exactly this shape:
{
  "decisions": [
    {"content": "string", "participants": ["string"], "access_level": "general"}
  ],
  "tasks": [
    {"description": "string", "owner": "string", "deadline": "string", "status": "open"}
  ]
}
If a field is unknown, use an empty string. access_level should be "leadership" only
if the decision clearly involves HR, compensation, or confidential strategy, otherwise "general".
"""


def extract_from_transcript(transcript: str, meeting_id: str, user_id: str = "hackathon@demo.com"):
    client = get_client()
    prompt = EXTRACTION_SYSTEM_PROMPT + "\n\nTranscript:\n" + transcript

    resp = client.inference.chat({
        "user_id": user_id,
        "agent_id": EXTRACTION_AGENT_ID,
        "message": prompt,
        "session_id": f"extract-{meeting_id}",
    })

    # NOTE: print(resp) once the first time you run this. The SDK is alpha-stage
    # and the exact response key may differ. Adjust the line below if needed.
    if isinstance(resp, dict):
        raw = resp.get("response") or resp.get("message") or str(resp)
    else:
        raw = str(resp)

    raw = re.sub(r"^```json|```$", "", raw.strip(), flags=re.MULTILINE).strip()

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"decisions": [], "tasks": [], "_raw_error": raw}

    data.setdefault("decisions", [])
    data.setdefault("tasks", [])
    return data
