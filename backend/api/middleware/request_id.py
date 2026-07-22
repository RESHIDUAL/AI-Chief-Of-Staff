"""Request ID middleware for end-to-end tracing through application logs."""

import uuid
import logging
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Injects a unique X-Request-ID into every request for log correlation.
    
    Reuses meeting_id from the request body when available, otherwise generates
    a new UUID. The ID is logged as a structured field and returned in the
    response header for client-side correlation.
    """

    async def dispatch(self, request: Request, call_next):
        # Prefer existing header, then generate
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4())[:12])
        
        # Attach to request state for downstream access
        request.state.request_id = request_id
        
        logger.info(
            f"[rid={request_id}] {request.method} {request.url.path}"
        )
        
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
