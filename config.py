import os
from dotenv import load_dotenv

load_dotenv()

LYZR_API_KEY = os.getenv("LYZR_AGENT_API_KEY")
EXTRACTION_AGENT_ID = os.getenv("LYZR_EXTRACTION_AGENT_ID")
RAG_AGENT_ID = os.getenv("LYZR_RAG_AGENT_ID")

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "org_memory"

EMBED_MODEL_NAME = "all-MiniLM-L6-v2"
EMBED_DIM = 384
