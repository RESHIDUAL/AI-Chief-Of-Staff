"""Rate limiting middleware using slowapi (60 req/min per client)."""

import logging

logger = logging.getLogger(__name__)

try:
    from slowapi import Limiter
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded
    from slowapi.middleware import SlowAPIMiddleware

    limiter = Limiter(key_func=get_remote_address, default_limits=["60/minute"])
    SLOWAPI_AVAILABLE = True
except ImportError:
    limiter = None
    SLOWAPI_AVAILABLE = False
    logger.info("slowapi not installed. Rate limiting disabled.")


def setup_rate_limiting(app):
    """Attach rate limiter to FastAPI app if slowapi is available."""
    if SLOWAPI_AVAILABLE and limiter:
        app.state.limiter = limiter
        app.add_middleware(SlowAPIMiddleware)
        logger.info("Rate limiting enabled: 60 requests/minute per client.")
    else:
        logger.info("Rate limiting not available (slowapi not installed).")
