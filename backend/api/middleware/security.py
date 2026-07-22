"""Security Middleware — Rate Limiting, Input Sanitation, and Security Headers.

Provides data protection for Phase 5.
"""

import time
import html
import logging
from collections import defaultdict
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

logger = logging.getLogger(__name__)


# ── Sliding Window Rate Limiter ────────────────────────────────────────

class RateLimiter:
    """Sliding-window rate limiter per client IP address."""

    def __init__(self, requests_per_minute: int = 60):
        self.rpm = requests_per_minute
        self.window = 60.0  # seconds
        self.requests: dict[str, list[float]] = defaultdict(list)

    def is_allowed(self, client_ip: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        # Clean old timestamps
        self.requests[client_ip] = [
            t for t in self.requests[client_ip] if t > cutoff
        ]

        if len(self.requests[client_ip]) >= self.rpm:
            return False

        self.requests[client_ip].append(now)
        return True


rate_limiter = RateLimiter(requests_per_minute=120)


# ── Security & Data Protection Middleware ──────────────────────────────

class SecurityMiddleware(BaseHTTPMiddleware):
    """Enforces security HTTP headers and rate limits across API endpoints."""

    async def dispatch(self, request: Request, call_next) -> Response:
        client_ip = request.client.host if request.client else "unknown"

        # Rate limiting check (skip health check endpoint)
        if request.url.path != "/health" and not rate_limiter.is_allowed(client_ip):
            logger.warning(f"Rate limit exceeded for IP: {client_ip}")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please try again later.",
            )

        response = await call_next(request)

        # Enforce security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = (
            "max-age=31536000; includeSubDomains"
        )
        return response


# ── Input Sanitizer Helper ─────────────────────────────────────────────

def sanitize_input_text(text: str) -> str:
    """Sanitize input string by escaping HTML characters to prevent XSS."""
    if not text:
        return ""
    # Strip dangerous HTML tags while preserving text formatting
    cleaned = html.escape(text.strip())
    return cleaned
