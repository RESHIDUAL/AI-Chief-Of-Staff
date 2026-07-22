# AI Chief of Staff — 2-Day Hackathon Build

Scoped-down version of the full PRD. Cut for time: Google Drive/Pub/Sub ingestion
(paste transcript instead), PostgreSQL (Qdrant payload holds metadata), React
(Streamlit instead), LangGraph (plain function calls instead — you don't need a
graph framework for two agent calls in sequence).

Kept, because these are what actually make this more than a summarizer:
Decisions vs Tasks as separate entities, human-in-the-loop approval, the
correction feedback loop (edit → re-embed), and RBAC-filtered retrieval.

## Architecture (trimmed)

```
Transcript paste
      │
      ▼
Extraction Agent (Lyzr Studio agent) ──► JSON {decisions[], tasks[]}
      │
      ▼
HITL Review (Streamlit) — edit, approve
      │
      ▼
Embed (sentence-transformers) ──► Qdrant (payload = metadata incl. access_level)
      │
      ▼
RAG Chat: query ──► embed ──► Qdrant search (filtered by role) ──► context
      │
      ▼
RAG Chat Agent (Lyzr Studio agent) ──► answer
```

## Setup (do this first, ~30 min)

### 1. Qdrant Cloud (faster than Docker for a 2-day sprint)
1. Sign up at https://cloud.qdrant.io (free tier).
2. Create a cluster, copy the URL and API key into `.env`.

### 2. Lyzr Studio — create two agents
Go to Lyzr's agent studio, sign up, create two agents:

**Agent 1: "Extraction Agent"**
Paste the system prompt from `EXTRACTION_SYSTEM_PROMPT` in `extraction_agent.py`
as its instructions. Copy its agent ID into `LYZR_EXTRACTION_AGENT_ID`.

**Agent 2: "RAG Chat Agent"**
Paste the system prompt from `RAG_SYSTEM_PROMPT` in `rag_agent.py` as its
instructions. Copy its agent ID into `LYZR_RAG_AGENT_ID`.

Get your Lyzr API key from account settings, put it in `LYZR_AGENT_API_KEY`.

### 3. Local environment
```bash
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt
copy .env.example .env         # then fill in the values
```

### 4. First run — verify the SDK response shape
`lyzr-python-sdk` is alpha-stage, released Aug 2025. Before you trust it, run:
```python
python -c "
from extraction_agent import get_client
from config import EXTRACTION_AGENT_ID
r = get_client().inference.chat({'user_id':'test@demo.com','agent_id':EXTRACTION_AGENT_ID,'message':'Say hello in JSON: {\"hello\":\"world\"}'})
print(r)
"
```
Look at the printed shape. If the response isn't under `resp["response"]`,
fix the one line in `extraction_agent.py` and `rag_agent.py` that reads it.
Do this now, not during the demo.

### 5. Run the app
```bash
streamlit run app.py
```

## Day-by-day plan

**Day 1 morning:** Qdrant Cloud + Lyzr Studio signup, create both agents,
verify the SDK response shape (step 4 above). This is the highest-risk part —
get it working before you build anything on top of it.

**Day 1 afternoon:** Wire up `qdrant_store.py` and `embeddings.py`, test with
a hardcoded transcript, confirm items land in Qdrant with correct payload.

**Day 1 evening:** Build tab 1 (Ingest & Extract) and tab 2 (Review). Test the
full loop: paste transcript → extract → edit → approve → see it land in Qdrant.

**Day 2 morning:** Build tab 3 (RAG Chat) with the role filter. Test that an
"employee" role genuinely can't retrieve a "leadership" item — this is your
RBAC demo, judges will ask about it.

**Day 2 afternoon:** Test the correction feedback loop end to end (edit a
committed item, confirm the vector actually changes — search for the old
wording and the new wording, show both results differ). Write 3-4 realistic
demo transcripts in advance (one with a leadership-only decision in it) so you
aren't typing during the demo.

**Day 2 evening:** Polish, rehearse a 3-minute walkthrough: ingest → review →
ask a question → edit a wrong item → ask the same question again and show the
answer changed.

## Demo script (3 minutes)

1. Paste a transcript with 2 decisions + 2 tasks, one decision marked leadership-only.
2. Extract, show the JSON split into two streams.
3. Approve everything in Review tab.
4. Switch to Chat tab as "employee," ask about the leadership decision — show
   it's not retrieved.
5. Switch role to "leadership," ask the same question — show it now answers.
6. Go back to Review, deliberately "correct" a task's owner name, save.
7. Ask the chat agent who owns that task — show it now returns the corrected name.

That last step is the whole point of the "self-improving memory" pitch. Make
sure it works before the demo, not during it.
