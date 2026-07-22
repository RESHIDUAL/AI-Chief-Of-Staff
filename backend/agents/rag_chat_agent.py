"""RAG Chat Agent — answers natural language user queries using retrieved organizational memory.

Enforces CRISPE-structured prompting, Entity-Specific Precision Guardrails,
and strict role-based memory synthesis.
"""

import logging
import re
import hashlib
from lyzr_python_sdk import LyzrAgentAPI
from backend.config.settings import settings
from backend.observability.tracing import agent_span

logger = logging.getLogger(__name__)
_client: LyzrAgentAPI | None = None


def get_client() -> LyzrAgentAPI:
    """Get or create Lyzr API client singleton."""
    global _client
    if _client is None:
        _client = LyzrAgentAPI(api_key=settings.LYZR_AGENT_API_KEY)
    return _client


# ── CRISPE-Structured RAG System Prompt ────────────────────────────────
RAG_SYSTEM_PROMPT = """
## CAPACITY / ROLE
You are the AI Chief of Staff RAG Agent for an enterprise executive system.
Your job is to answer user questions using ONLY the retrieved context chunks from
organizational memory.

## INSIGHT
You serve C-suite executives, project managers, and employees. Users rely on you
for accurate recall of past meeting decisions, task ownerships, and deadlines.
False information or mixing up task owners undermines trust.

## CRITICAL EXECUTION RULES (GUARDRAILS)
1. **Entity-Specific Precision (Filtering)**: If a user query explicitly asks about a specific person (e.g. "Ananya", "Rohan", "Amit", "Vikram", "Sneha", "Neha", "Kabir"), you MUST include ONLY items where that person is explicitly designated as the owner or subject. Do NOT dump chunks belonging to other individuals.
2. **Item Type Precision (Task vs Decision)**: If the user asks for "tasks" or "action items" for a specific person, check if any tasks exist. If no tasks exist for that person (e.g. only a decision involves them), explicitly clarify that no tasks are assigned, but mention the decision if relevant.
3. **Strict Synthesis**: Formulate your response using exclusively matching context chunks. Completely omit retrieved chunks that belong to other team members or unmatching metadata categories.
4. **No Hallucination**: Rely strictly on facts in the context. Never invent tasks, owners, or deadlines.
5. **Meeting Citations**: Cite the meeting name for every fact you include.

## PERSONALITY
Be direct, concise, and executive-friendly. Use bullet points for multiple items.
"""

KNOWN_NAMES = ["ananya", "rohan", "neha", "kabir", "amit", "sneha", "vikram", "sarah", "eshwar"]


def _extract_person_name_from_query(query: str) -> str | None:
    """Detect if a user query explicitly asks about a specific person."""
    query_lower = query.lower()
    for n in KNOWN_NAMES:
        if re.search(rf"\b{n}\b", query_lower):
            return n.capitalize()

    # A capitalized verb at the start of an action description (for example,
    # "Who was assigned to Coordinate ...?") is not a person's name.  Only
    # infer an arbitrary name when it is the complete target of the clause.
    match = re.search(r"\b(for|to|by|is|doing|about|owner|assigned to|assigned for)\s+([A-Z][a-z]+)(?:\?|$)", query)
    if match:
        name = match.group(2)
        if name.lower() not in ("what", "which", "how", "who", "when", "where", "why", "the", "a", "an", "all", "our", "task", "tasks"):
            return name

    possess = re.search(r"\b([A-Z][a-z]+)'s\b", query)
    if possess:
        return possess.group(1)

    return None


def _synthesize_fallback_answer(query: str, context: str) -> str:
    """Direct contextual synthesis engine enforcing Entity-Specific Precision Guardrails."""
    if not context.strip():
        return "No relevant organizational memory found for your query and access level."

    lines = [line.strip() for line in context.split("\n") if line.strip().startswith("-")]

    target_person = _extract_person_name_from_query(query)
    is_task_query = any(w in query.lower() for w in ["task", "tasks", "action item", "todo", "assigned"])

    if target_person:
        # Filter lines involving target person
        person_lines = [l for l in lines if target_person.lower() in l.lower()]
        
        if not person_lines:
            return f"No organizational memory records found explicitly assigned to or involving **{target_person}**."

        if is_task_query:
            # Filter specifically for tasks assigned to target person
            task_lines = [l for l in person_lines if "[task]" in l.lower() or "owner:" in l.lower()]
            if task_lines:
                formatted_facts = "\n".join([f"• {l.lstrip('- ')}" for l in task_lines])
                return f"Here are the tasks assigned to **{target_person}**:\n\n{formatted_facts}"
            else:
                decision_lines = [l for l in person_lines if "[decision]" in l.lower() or "agreed" in l.lower()]
                dec_text = "\n".join([f"• {l.lstrip('- ')}" for l in decision_lines])
                return f"No tasks are currently assigned to **{target_person}** in organizational memory. **{target_person}** is involved in the following decision(s):\n\n{dec_text}"
        else:
            formatted_facts = "\n".join([f"• {l.lstrip('- ')}" for l in person_lines])
            return f"Here is the organizational memory matching **{target_person}**:\n\n{formatted_facts}"

    if not lines:
        return f"Based on organizational memory records:\n{context}"

    formatted_facts = "\n".join([f"• {l.lstrip('- ')}" for l in lines[:5]])
    return f"Based on organizational memory records, here is the matching information:\n\n{formatted_facts}"


def answer_query(
    query: str,
    context: str,
    user_id: str = "hackathon@demo.com",
    session_id: str = "org-memory-chat",
) -> str:
    """Send query + context to Lyzr RAG Chat Agent or synthesize direct contextual answer with entity guardrails."""
    with agent_span("rag_chat_agent", "answer_query", {
        "session_id": session_id,
        "model": "lyzr_rag",
        "prompt_token_count": (len(query) + len(context)) // 4,
        "prompt_fingerprint": hashlib.sha256(RAG_SYSTEM_PROMPT.encode()).hexdigest()[:16],
    }) as span:
        try:
            client = get_client()
            prompt = f"{RAG_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {query}"

            resp = client.inference.chat(
                {
                    "user_id": user_id,
                    "agent_id": settings.LYZR_RAG_AGENT_ID,
                    "message": prompt,
                    "session_id": session_id,
                }
            )

            if isinstance(resp, dict):
                answer = resp.get("response") or resp.get("message") or ""
            else:
                answer = str(resp)

            if not answer or "error" in answer.lower() or answer.startswith("{"):
                ret = _synthesize_fallback_answer(query, context)
            else:
                # Post-process answer to enforce Entity Precision Guardrails
                target_person = _extract_person_name_from_query(query)
                if target_person and target_person.lower() not in answer.lower():
                    ret = _synthesize_fallback_answer(query, context)
                else:
                    ret = answer
        except Exception as e:
            logger.warning(f"Lyzr RAG API call fallback triggered: {e}")
            ret = _synthesize_fallback_answer(query, context)

        if span:
            span.set_attribute("completion_token_count", str(len(ret) // 4))
        return ret
