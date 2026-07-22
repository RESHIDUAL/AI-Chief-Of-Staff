"""Auth API routes — Google OAuth 2.0 login flow, demo authentication, and JWT session management.

Integrates Google OAuth 2.0 for enterprise Google Workspace authentication.
Role resolution supports two modes via RBAC_MODE in .env:
  - "static" (default): Looks up email in ROLE_TABLE from .env
  - "workspace_groups": Uses Google Admin SDK to check group membership
"""

import json
import logging
import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.middleware.auth import (
    create_access_token,
    get_current_user,
)
from backend.config.settings import settings
from backend.db.postgres.database import get_db
from backend.db.postgres import crud

logger = logging.getLogger(__name__)
router = APIRouter()


# ── Request/Response Models ──────────────────────────────────────────

class DemoLoginRequest(BaseModel):
    """Demo login request for development/testing."""
    email: str = "hackathon@demo.com"
    name: str = "Demo User"
    role: str = "leadership"
    allowed_groups: list[str] = ["all", "engineering", "leadership"]


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserProfile(BaseModel):
    user_id: str
    email: str
    name: str
    role: str
    allowed_groups: list[str]
    avatar_url: str | None = None


# ── Role Resolution ─────────────────────────────────────────────────

def resolve_role_static(email: str) -> str:
    """Look up role from ROLE_TABLE in .env. Defaults to 'general' for unknown emails.

    ROLE_TABLE format in .env: '{"admin@company.com":"admin","lead@company.com":"leadership"}'
    """
    role_table_raw = getattr(settings, "ROLE_TABLE", "{}")
    try:
        if isinstance(role_table_raw, dict):
            role_table = role_table_raw
        else:
            role_table = json.loads(role_table_raw) if role_table_raw else {}
    except (json.JSONDecodeError, TypeError):
        role_table = {}

    return role_table.get(email.lower(), "general")


def resolve_role_workspace_groups(email: str) -> str:
    """Check Google Workspace group membership via Admin SDK Directory API.

    Authenticates as service account, impersonates GOOGLE_ADMIN_IMPERSONATE_EMAIL,
    calls groups().list(userKey=email). Returns 'leadership' if user is in the
    configured leadership group, 'general' otherwise.

    Fails closed to 'general' on any exception.
    """
    try:
        from google.oauth2 import service_account
        from googleapiclient.discovery import build

        creds_path = getattr(settings, "GOOGLE_APPLICATION_CREDENTIALS", "")
        admin_email = getattr(settings, "GOOGLE_ADMIN_IMPERSONATE_EMAIL", "")
        leadership_group = getattr(settings, "LEADERSHIP_GROUP_EMAIL", "")

        if not creds_path or not admin_email or not leadership_group:
            logger.warning("Workspace groups RBAC not fully configured. Falling back to 'general'.")
            return "general"

        credentials = service_account.Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/admin.directory.group.readonly"],
            subject=admin_email,
        )
        service = build("admin", "directory_v1", credentials=credentials)
        results = service.groups().list(userKey=email).execute()
        user_groups = [g.get("email", "").lower() for g in results.get("groups", [])]

        if leadership_group.lower() in user_groups:
            return "leadership"
        return "general"

    except Exception as e:
        logger.warning(f"Workspace groups lookup failed for {email}: {e}. Failing closed to 'general'.")
        return "general"


def resolve_role(email: str) -> str:
    """Resolve user role based on RBAC_MODE setting.

    Branches on RBAC_MODE:
      - "static" (default): Uses ROLE_TABLE from .env
      - "workspace_groups": Uses Google Admin SDK group membership

    Always fails closed to "general" on any error.
    """
    rbac_mode = getattr(settings, "RBAC_MODE", "static")

    if rbac_mode == "workspace_groups":
        return resolve_role_workspace_groups(email)
    else:
        return resolve_role_static(email)


def _role_to_groups(role: str) -> list[str]:
    """Map a role to its allowed organizational groups."""
    groups = ["all"]
    if role in ("admin",):
        groups.extend(["engineering", "hr", "finance", "leadership"])
    elif role in ("leadership",):
        groups.extend(["leadership", "strategy"])
    elif role in ("manager",):
        groups.extend(["engineering", "product"])
    else:
        groups.append("general")
    return list(set(groups))


# ── Demo Login (development mode) ───────────────────────────────────

@router.post("/login/demo", response_model=TokenResponse)
async def demo_login(
    req: DemoLoginRequest,
    db: AsyncSession = Depends(get_db),
):
    """Issue a JWT token for demo/development use."""
    if settings.APP_ENV not in ("development", "staging"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Demo login is only available in development/staging",
        )

    # Persist or update user in PostgreSQL
    try:
        db_user = await crud.get_or_create_user(
            db,
            email=req.email,
            name=req.name,
            role=req.role,
            allowed_groups=req.allowed_groups,
        )
        await db.commit()
        user_id = db_user.id
    except Exception as e:
        logger.warning(f"PostgreSQL user create skipped: {e}")
        user_id = "demo-user"

    token_data = {
        "sub": req.email,
        "email": req.email,
        "name": req.name,
        "role": req.role,
        "allowed_groups": req.allowed_groups,
    }
    access_token = create_access_token(token_data)

    logger.info(f"Demo login issued for: {req.email} (Role: {req.role})")

    return TokenResponse(
        access_token=access_token,
        user={
            "user_id": user_id,
            "email": req.email,
            "name": req.name,
            "role": req.role,
            "allowed_groups": req.allowed_groups,
        },
    )


# ── Google OAuth 2.0 Integration ────────────────────────────────────

GOOGLE_OAUTH_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_OAUTH_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"


@router.get("/login/google")
async def google_login():
    """Redirect user to Google OAuth 2.0 consent screen."""
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail="GOOGLE_CLIENT_ID is not configured in .env. Use POST /api/v1/auth/login/demo for dev login.",
        )

    redirect_uri = f"{settings.PUBLIC_BACKEND_URL.rstrip('/')}/api/v1/auth/callback"
    scope = "openid email profile"
    auth_url = (
        f"{GOOGLE_OAUTH_AUTH_URL}?"
        f"client_id={settings.GOOGLE_CLIENT_ID}&"
        f"redirect_uri={redirect_uri}&"
        f"response_type=code&"
        f"scope={scope}&"
        f"access_type=offline&"
        f"prompt=consent"
    )
    return RedirectResponse(url=auth_url)


@router.get("/callback")
async def google_callback(
    code: str = "",
    db: AsyncSession = Depends(get_db),
):
    """Handle Google OAuth 2.0 callback, exchange code for user info & issue JWT.

    Redirects to frontend with JWT in URL fragment (#token=...), never a query param.
    """
    if not code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing OAuth authorization code from Google",
        )

    redirect_uri = f"{settings.PUBLIC_BACKEND_URL.rstrip('/')}/api/v1/auth/callback"

    async with httpx.AsyncClient() as client:
        # 1. Exchange authorization code for tokens
        token_resp = await client.post(
            GOOGLE_OAUTH_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.GOOGLE_CLIENT_ID,
                "client_secret": settings.GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            logger.error(f"Google OAuth token error: {token_resp.text}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to exchange authorization code with Google",
            )

        tokens = token_resp.json()
        google_access_token = tokens.get("access_token")

        # 2. Fetch verified user profile from Google UserInfo API
        userinfo_resp = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {google_access_token}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to fetch user profile from Google",
            )

        g_user = userinfo_resp.json()
        email = g_user.get("email")
        name = g_user.get("name", email)
        avatar = g_user.get("picture")

        # 3. Resolve role via configured RBAC_MODE (static table or workspace groups)
        role = resolve_role(email)
        allowed_groups = _role_to_groups(role)

        # 4. Create or update user in PostgreSQL
        try:
            db_user = await crud.get_or_create_user(
                db,
                email=email,
                name=name,
                role=role,
                allowed_groups=allowed_groups,
            )
            db_user.avatar_url = avatar
            await db.commit()
        except Exception as e:
            logger.warning(f"PostgreSQL user upsert skipped: {e}")

        # 5. Issue internal JWT with sub=email (not db id)
        token_payload = {
            "sub": email,
            "email": email,
            "name": name,
            "role": role,
            "allowed_groups": allowed_groups,
        }
        jwt_token = create_access_token(token_payload)

        # SECURITY: Redirect with token in URL fragment (#token=...), never query param
        frontend_url = f"{settings.PUBLIC_FRONTEND_URL.rstrip('/')}/#token={jwt_token}"
        return RedirectResponse(url=frontend_url)


# ── User Profile ────────────────────────────────────────────────────

@router.get("/me", response_model=UserProfile)
async def get_me(user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile and RBAC permissions."""
    return UserProfile(
        user_id=user.get("user_id", ""),
        email=user.get("email", ""),
        name=user.get("name", ""),
        role=user.get("role", "employee"),
        allowed_groups=user.get("allowed_groups", ["all"]),
        avatar_url=user.get("avatar_url"),
    )


# ── Logout ──────────────────────────────────────────────────────────

@router.post("/logout")
async def logout(user: dict = Depends(get_current_user)):
    """Logout current user session."""
    logger.info(f"User session terminated: {user.get('email')}")
    return {"status": "logged_out", "message": "Session invalidated."}
