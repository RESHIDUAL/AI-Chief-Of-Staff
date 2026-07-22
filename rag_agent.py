from lyzr_python_sdk import LyzrAgentAPI
from config import LYZR_API_KEY, RAG_AGENT_ID

_client = None


def get_client():
    global _client
    if _client is None:
        _client = LyzrAgentAPI(api_key=LYZR_API_KEY)
    return _client


# Paste this as the system prompt of your "RAG Chat Agent" in Lyzr Studio.
RAG_SYSTEM_PROMPT = """You are the RAG Chat Agent for an organizational memory system.
Answer the user's question using ONLY the provided context, which was retrieved from
Qdrant and already filtered for the user's access level. If the context does not
contain the answer, say plainly that organizational memory has no record of this yet.
Cite which meeting each fact came from when the context includes a meeting name.
Keep answers short and direct."""


def answer_query(query: str, context: str, user_id: str = "hackathon@demo.com"):
    client = get_client()
    prompt = f"{RAG_SYSTEM_PROMPT}\n\nContext:\n{context}\n\nQuestion: {query}"

    resp = client.inference.chat({
        "user_id": user_id,
        "agent_id": RAG_AGENT_ID,
        "message": prompt,
        "session_id": "org-memory-chat",
    })

    if isinstance(resp, dict):
        return resp.get("response") or resp.get("message") or str(resp)
    return str(resp)
