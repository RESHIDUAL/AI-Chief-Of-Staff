"""Qdrant vector database operations for organizational memory with multi-version SDK compatibility."""

# ────────────────────────────────────────────────────────────────────────────────
# INVARIANT: Single Write Path Through Memory Agent
# 
# All writes to Qdrant (upsert_item, upsert_batch) and PostgreSQL CRUD operations
# MUST go through the Memory Agent (backend/agents/memory_agent.py) which is
# invoked exclusively by:
#   - review.py: approve_decision, approve_task, batch_approve, edit_committed_item
#   - pipeline_graph.py: node_auto_embed (for high-confidence auto-approval)
#
# Direct writes from ingestion.py are PROHIBITED. Ingestion stores raw meeting
# metadata in PostgreSQL only; vector embedding is deferred to the review/approval
# step to enforce the Human-in-the-Loop guarantee.
# ────────────────────────────────────────────────────────────────────────────────

import logging
import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    MatchAny,
)
from backend.config.settings import settings

logger = logging.getLogger(__name__)
_client: QdrantClient | None = None


def get_client() -> QdrantClient:
    """Get or create Qdrant client singleton."""
    global _client
    if _client is None:
        _client = QdrantClient(
            url=settings.QDRANT_URL,
            api_key=settings.QDRANT_API_KEY,
            prefer_grpc=settings.QDRANT_PREFER_GRPC,
        )
    return _client


def init_collection() -> None:
    """Create the org_memory collection if it doesn't exist."""
    try:
        client = get_client()
        existing = [c.name for c in client.get_collections().collections]
        if settings.QDRANT_COLLECTION_NAME not in existing:
            client.create_collection(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vectors_config=VectorParams(
                    size=settings.EMBED_DIM, distance=Distance.COSINE
                ),
            )
    except Exception as e:
        logger.warning(f"Qdrant collection init skipped ({e})")


def upsert_item(
    vector: list[float], payload: dict, point_id: str | None = None
) -> str:
    """Insert or update a single point in Qdrant."""
    pid = point_id or str(uuid.uuid4())
    try:
        client = get_client()
        client.upsert(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points=[PointStruct(id=pid, vector=vector, payload=payload)],
        )
    except Exception as e:
        logger.warning(f"Qdrant upsert skipped ({e})")
    return pid


def upsert_batch(
    vectors: list[list[float]], payloads: list[dict], point_ids: list[str] | None = None
) -> list[str]:
    """Batch upsert multiple points into Qdrant."""
    ids = point_ids or [str(uuid.uuid4()) for _ in vectors]
    try:
        client = get_client()
        points = [
            PointStruct(id=pid, vector=vec, payload=pl)
            for pid, vec, pl in zip(ids, vectors, payloads)
        ]
        client.upsert(collection_name=settings.QDRANT_COLLECTION_NAME, points=points)
    except Exception as e:
        logger.warning(f"Qdrant batch upsert skipped ({e})")
    return ids


def search(
    vector: list[float],
    access_level: str | None = None,
    allowed_groups: list[str] | None = None,
    item_type: str | None = None,
    limit: int = 5,
) -> list:
    """Search Qdrant with optional RBAC filtering across qdrant-client SDK versions."""
    must = []
    if access_level:
        must.append(
            FieldCondition(key="access_level", match=MatchValue(value=access_level))
        )
    if allowed_groups:
        must.append(
            FieldCondition(
                key="allowed_groups", match=MatchAny(any=allowed_groups)
            )
        )
    if item_type:
        must.append(
            FieldCondition(key="type", match=MatchValue(value=item_type))
        )
    query_filter = Filter(must=must) if must else None

    try:
        client = get_client()
        if hasattr(client, "query_points"):
            res = client.query_points(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query=vector,
                query_filter=query_filter,
                limit=limit,
            )
            return getattr(res, "points", [])
        elif hasattr(client, "search"):
            return client.search(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                query_vector=vector,
                query_filter=query_filter,
                limit=limit,
            )
        elif hasattr(client, "search_points"):
            res = client.search_points(
                collection_name=settings.QDRANT_COLLECTION_NAME,
                vector=vector,
                query_filter=query_filter,
                limit=limit,
            )
            return getattr(res, "points", [])
    except Exception as e:
        logger.warning(f"Qdrant vector search skipped ({e})")

    return []


def get_all(limit: int = 200) -> list:
    """Scroll all points in the collection."""
    try:
        client = get_client()
        points, _ = client.scroll(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            limit=limit,
            with_payload=True,
            with_vectors=False,
        )
        return points
    except Exception as e:
        logger.warning(f"Qdrant scroll skipped ({e})")
        return []


def delete_item(point_id: str) -> None:
    """Delete a single point by ID."""
    try:
        client = get_client()
        client.delete(
            collection_name=settings.QDRANT_COLLECTION_NAME,
            points_selector=[point_id],
        )
    except Exception as e:
        logger.warning(f"Qdrant delete skipped ({e})")
