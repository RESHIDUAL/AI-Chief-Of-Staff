"""Query API routes — RAG Chat with Hybrid Vector + Keyword Retrieval and RBAC Filtering."""

import logging
import re
import uuid
from fastapi import APIRouter, Depends

from backend.api.models.schemas import QueryRequest, QueryResponse, SourceCitation
from backend.api.middleware.auth import get_current_user
from backend.api.middleware.rbac import get_qdrant_access_filter, get_qdrant_group_filter
from backend.db.embeddings import embed_text
from backend.db.qdrant_store import search, get_all
from backend.agents.rag_chat_agent import answer_query, _extract_person_name_from_query

logger = logging.getLogger(__name__)
router = APIRouter()

# In-memory conversation history (per session) for multi-turn chat
_conversations: dict[str, list[dict]] = {}

STOP_WORDS = {"what", "who", "where", "when", "why", "how", "is", "are", "was", "were", "the", "a", "an", "for", "to", "in", "on", "of", "and", "or", "did", "we", "do", "about", "tasks", "task", "decisions", "assigned"}


def _extract_query_keywords(query: str) -> list[str]:
    """Extract significant keywords from natural language query."""
    words = re.findall(r"\b[A-Za-z0-9_-]+\b", query.lower())
    return [w for w in words if w not in STOP_WORDS and len(w) > 1]


def _payload_is_accessible(payload: dict, user_role: str, user_groups: list[str]) -> bool:
    """Apply the same RBAC checks to fallback scans as vector queries."""
    if user_role not in ("leadership", "admin") and payload.get("access_level", "general") != "general":
        return False
    allowed_groups = payload.get("allowed_groups", ["all"])
    return "all" in user_groups or "all" in allowed_groups or bool(set(user_groups) & set(allowed_groups))


def _is_assignment_lookup(query: str) -> bool:
    """Identify questions asking for the owner of a described action item."""
    return bool(re.search(r"\bwho\s+(?:was|is)\s+assigned\s+to\b", query, re.IGNORECASE))


def _assignment_keywords(query: str) -> list[str]:
    """Keep only the requested action phrase, excluding 'who was assigned to'."""
    subject = re.sub(r"^\s*who\s+(?:was|is)\s+assigned\s+to\s+", "", query, flags=re.IGNORECASE)
    return _extract_query_keywords(subject)


def _assignment_answer(payload: dict) -> str:
    """Deterministically answer an owner lookup from the single best matching task."""
    owner = payload.get("owner") or "No owner is recorded"
    description = payload.get("description") or payload.get("content", "").replace("Task: ", "").split(". Owner:")[0]
    deadline = payload.get("deadline")
    meeting = payload.get("meeting_name", "the meeting record")
    answer = f"**{owner}** was assigned to **{description}** in *{meeting}*."
    if deadline:
        answer += f" Deadline: **{deadline}**."
    return answer


@router.post("/", response_model=QueryResponse)
async def query_organizational_memory(
    req: QueryRequest,
    user: dict = Depends(get_current_user),
):
    """Ask a natural language question against organizational memory using Hybrid Retrieval (Vector + Keyword)."""
    # Role comes EXCLUSIVELY from the JWT — never from the request body
    user_role = user.get("role", "employee")
    user_groups = user.get("allowed_groups", ["all"])
    session_id = req.session_id or str(uuid.uuid4())

    logger.info(f"RAG query from role={user_role}, session={session_id}: {req.query[:80]}...")

    candidate_map: dict[str, dict] = {}
    assignment_lookup = _is_assignment_lookup(req.query)

    # 1. Vector Search in Qdrant
    try:
        query_vector = embed_text(req.query)
        access_filter = get_qdrant_access_filter(user_role)
        group_filter = get_qdrant_group_filter(user_groups)

        vector_results = search(
            vector=query_vector,
            access_level=access_filter,
            allowed_groups=group_filter,
            item_type="task" if assignment_lookup else None,
            limit=10,
        )

        for r in vector_results:
            pid = str(getattr(r, "id", uuid.uuid4()))
            payload = getattr(r, "payload", {}) or {}
            candidate_map[pid] = {
                "point": r,
                "payload": payload,
                "vector_score": float(getattr(r, "score", 0.85)),
                "keyword_score": 0.0,
            }
    except Exception as e:
        logger.warning(f"Qdrant vector search skipped: {e}")

    # 2. Ingest points from Qdrant get_all
    try:
        all_points = get_all(limit=100)
        for p in all_points:
            pid = str(getattr(p, "id", uuid.uuid4()))
            payload = getattr(p, "payload", {}) or {}
            
            if not _payload_is_accessible(payload, user_role, user_groups):
                continue
            if assignment_lookup and payload.get("type") != "task":
                continue

            if pid not in candidate_map:
                candidate_map[pid] = {
                    "point": p,
                    "payload": payload,
                    "vector_score": 0.6,
                    "keyword_score": 0.0,
                }
    except Exception as e:
        logger.warning(f"Qdrant get_all skipped: {e}")

    keywords = _assignment_keywords(req.query) if assignment_lookup else _extract_query_keywords(req.query)
    target_person = _extract_person_name_from_query(req.query)

    # Entity-Specific Precision Filter: If query names a specific person, keep ONLY matching candidates
    if target_person:
        p_lower = target_person.lower()
        person_candidates = {}
        for pid, cand in candidate_map.items():
            payload = cand.get("payload", {})
            text_all = (
                str(payload.get("content", "")) + " " +
                str(payload.get("owner", "")) + " " +
                str(payload.get("description", "")) + " " +
                " ".join([str(p) for p in payload.get("participants", [])])
            ).lower()
            if p_lower in text_all:
                person_candidates[pid] = cand
        if person_candidates:
            candidate_map = person_candidates

    # Compute keyword matching score for all candidates
    for pid, cand in candidate_map.items():
        text_content = (cand["payload"].get("content", "") + " " + cand["payload"].get("meeting_name", "") + " " + cand["payload"].get("owner", "")).lower()
        if keywords:
            matches = sum(1 for kw in keywords if kw in text_content)
            cand["keyword_score"] = matches / len(keywords)

    # Hybrid Score = 0.6 * Vector + 0.4 * Keyword
    candidates = list(candidate_map.values())
    for cand in candidates:
        cand["final_score"] = (0.6 * cand["vector_score"]) + (0.4 * cand["keyword_score"])

    # Rank candidate items descending by final score
    candidates.sort(key=lambda x: x["final_score"], reverse=True)
    # Owner questions require an exact action match. Never pad this answer with
    # semantically adjacent tasks or decisions.
    if assignment_lookup:
        exact_matches = [c for c in candidates if c["keyword_score"] > 0]
        top_candidates = exact_matches[:1]
    else:
        top_candidates = candidates[:5]

    if not top_candidates:
        answer_text = "No relevant organizational memory found for your access level."
        return QueryResponse(answer=answer_text, sources=[], session_id=session_id)

    # 4. Build Context
    context_lines = []
    sources = []
    for cand in top_candidates:
        payload = cand["payload"]
        content = payload.get("content") or payload.get("description") or str(payload)
        meeting_name = payload.get("meeting_name", "Ingested Meeting")
        item_type = payload.get("type", "item")
        score = round(cand["final_score"], 3)

        context_lines.append(f"- ({meeting_name}) [{item_type}] {content}")
        sources.append(
            SourceCitation(
                content=content,
                item_type=item_type,
                meeting_name=meeting_name,
                score=score,
            )
        )

    context = "\n".join(context_lines)

    if assignment_lookup:
        answer_text = _assignment_answer(top_candidates[0]["payload"])
        if session_id not in _conversations:
            _conversations[session_id] = []
        _conversations[session_id].append({"query": req.query, "answer": answer_text})
        return QueryResponse(answer=answer_text, sources=sources, session_id=session_id)

    # Multi-turn conversation context
    history = _conversations.get(session_id, [])
    history_context = ""
    if history:
        history_lines = []
        for turn in history[-5:]:
            history_lines.append(f"User: {turn['query']}")
            history_lines.append(f"Assistant: {turn['answer']}")
        history_context = "\n\nPrevious conversation:\n" + "\n".join(history_lines) + "\n"

    full_context = history_context + "\nRetrieved organizational memory:\n" + context

    # 5. Synthesize Answer with RAG Agent
    answer_text = answer_query(
        query=req.query,
        context=full_context,
        session_id=session_id,
    )

    # Save to session history
    if session_id not in _conversations:
        _conversations[session_id] = []
    _conversations[session_id].append({
        "query": req.query,
        "answer": answer_text,
    })

    return QueryResponse(answer=answer_text, sources=sources, session_id=session_id)


@router.get("/sessions")
async def list_sessions(user: dict = Depends(get_current_user)):
    """List active chat sessions."""
    return [
        {
            "session_id": sid,
            "turns": len(turns),
            "last_query": turns[-1]["query"][:80] if turns else "",
        }
        for sid, turns in _conversations.items()
    ]


@router.get("/sessions/{session_id}")
async def get_session_history(session_id: str, user: dict = Depends(get_current_user)):
    """Get conversation history for a session."""
    history = _conversations.get(session_id)
    if not history:
        return {"session_id": session_id, "turns": []}
    return {"session_id": session_id, "turns": history}


@router.delete("/sessions/{session_id}")
async def clear_session(session_id: str, user: dict = Depends(get_current_user)):
    """Clear conversation history for a session."""
    if session_id in _conversations:
        del _conversations[session_id]
    return {"status": "cleared", "session_id": session_id}
