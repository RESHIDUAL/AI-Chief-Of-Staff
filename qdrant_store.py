import uuid
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, PointStruct, Filter, FieldCondition, MatchValue
)
from config import QDRANT_URL, QDRANT_API_KEY, COLLECTION_NAME, EMBED_DIM

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)


def init_collection():
    existing = [c.name for c in client.get_collections().collections]
    if COLLECTION_NAME not in existing:
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )


def upsert_item(vector, payload, point_id=None):
    pid = point_id or str(uuid.uuid4())
    client.upsert(
        collection_name=COLLECTION_NAME,
        points=[PointStruct(id=pid, vector=vector, payload=payload)],
    )
    return pid


def search(vector, access_level=None, item_type=None, limit=5):
    must = []
    if access_level:
        must.append(FieldCondition(key="access_level", match=MatchValue(value=access_level)))
    if item_type:
        must.append(FieldCondition(key="type", match=MatchValue(value=item_type)))
    query_filter = Filter(must=must) if must else None
    return client.search(
        collection_name=COLLECTION_NAME,
        query_vector=vector,
        query_filter=query_filter,
        limit=limit,
    )


def get_all(limit=200):
    points, _ = client.scroll(
        collection_name=COLLECTION_NAME, limit=limit, with_payload=True, with_vectors=False
    )
    return points


def delete_item(point_id):
    client.delete(collection_name=COLLECTION_NAME, points_selector=[point_id])
