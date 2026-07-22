"""JWT authentication middleware and utilities.

Handles token creation, verification, and the FastAPI dependency for extracting
the current authenticated user from the Authorization header.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, ExpiredSignatureError, jwt

from backend.config.settings import settings

logger = logging.getLogger(__name__)
security = HTTPBearer(auto_error=False)


def create_access_token(
    data: dict, expires_delta: Optional[timedelta] = None
) -> str:
    """Create a JWT access token with sub, role, name, iat, and exp claims."""
    to_encode = data.copy()
    now = datetime.now(timezone.utc)
    expire = now + (expires_delta or timedelta(minutes=settings.JWT_EXPIRY_MINUTES))
    to_encode.update({"iat": now, "exp": expire})
    return jwt.encode(
        to_encode, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM
    )


def decode_access_token(token: str) -> dict:
    """Decode and validate a JWT access token.

    Supports 'demo-token' fallback for development mode.
    """
    if token == "demo-token":
        return {
            "sub": "hackathon@demo.com",
            "email": "hackathon@demo.com",
            "name": "Demo User",
            "role": "leadership",
            "allowed_groups": ["all", "engineering", "leadership"],
        }

    try:
        payload = jwt.decode(
            token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM]
        )
        return payload
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session expired",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid session token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> dict:
    """Extract current user from JWT Bearer token in the Authorization header."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    return {
        "user_id": payload.get("sub", ""),
        "email": payload.get("email", ""),
        "name": payload.get("name", ""),
        "role": payload.get("role", "employee"),
        "allowed_groups": payload.get("allowed_groups", ["all"]),
    }


async def require_role(required_role: str, user: dict = Depends(get_current_user)) -> dict:
    """Dependency that checks the user has the required role."""
    role_hierarchy = {"admin": 4, "leadership": 3, "manager": 2, "employee": 1}
    user_level = role_hierarchy.get(user.get("role", "employee"), 1)
    required_level = role_hierarchy.get(required_role, 1)

    if user_level < required_level:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Requires {required_role} role or higher",
        )
    return user
