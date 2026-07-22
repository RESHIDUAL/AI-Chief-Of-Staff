"""AI Chief of Staff — FastAPI backend entry point."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.config.settings import settings
from backend.db.postgres.database import init_db
from backend.db.qdrant_store import init_collection
from backend.api.middleware.error_handler import ErrorHandlerMiddleware
from backend.api.middleware.security import SecurityMiddleware
from backend.api.middleware.request_id import RequestIdMiddleware
from backend.api.middleware.rate_limiter import setup_rate_limiting
from backend.api.routes import ingest, review, query, auth, pubsub

logging.basicConfig(
    level=logging.DEBUG if settings.APP_DEBUG else logging.INFO,
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle."""
    logger.info("Starting AI Chief of Staff backend...")
    # Initialize Qdrant collection
    init_collection()
    logger.info("Qdrant collection ready.")
    # Initialize PostgreSQL tables
    try:
        await init_db()
        logger.info("PostgreSQL tables ready.")
    except Exception as e:
        logger.warning(f"PostgreSQL init skipped: {e}")
    yield
    logger.info("Shutting down AI Chief of Staff backend.")


app = FastAPI(
    title="AI Chief of Staff API",
    description=(
        "Multi-agent organizational memory system — "
        "Decisions & Tasks as distinct entities with HITL review, "
        "correction feedback loop, and RBAC-filtered RAG."
    ),
    version="0.1.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Middleware stack (order matters — CORSMiddleware first)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityMiddleware)
app.add_middleware(RequestIdMiddleware)
setup_rate_limiting(app)

# Route registrations
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Auth"])
app.include_router(ingest.router, prefix="/api/v1/ingest", tags=["Ingestion"])
app.include_router(pubsub.router, prefix="/api/v1/ingest", tags=["Google ADK & Pub/Sub"])
app.include_router(review.router, prefix="/api/v1/review", tags=["Review (HITL)"])
app.include_router(query.router, prefix="/api/v1/query", tags=["Query (RAG)"])


@app.get("/health", tags=["System"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "ok",
        "environment": settings.APP_ENV,
        "version": "0.1.0",
    }


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "backend.main:app",
        host=settings.APP_HOST,
        port=settings.APP_PORT,
        reload=settings.APP_DEBUG,
    )
