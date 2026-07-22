"""Role-Based Access Control (RBAC) enforcement utilities."""

import logging

logger = logging.getLogger(__name__)

# Role hierarchy (higher number = more access)
ROLE_HIERARCHY = {
    "employee": 1,
    "manager": 2,
    "leadership": 3,
    "admin": 4,
}

# Access level to minimum role mapping
ACCESS_LEVEL_ROLES = {
    "general": "employee",
    "leadership": "leadership",
}


def user_can_access(user_role: str, access_level: str) -> bool:
    """Check if a user's role grants access to a given access level."""
    min_role = ACCESS_LEVEL_ROLES.get(access_level, "employee")
    user_rank = ROLE_HIERARCHY.get(user_role, 1)
    required_rank = ROLE_HIERARCHY.get(min_role, 1)
    return user_rank >= required_rank


def get_qdrant_access_filter(user_role: str) -> str | None:
    """Return the Qdrant access_level filter for a given user role.

    Leadership and admin see everything (returns None = no filter).
    Everyone else only sees 'general' items.
    """
    if user_role in ("leadership", "admin"):
        return None  # No filter — see all
    return "general"


def get_qdrant_group_filter(user_groups: list[str]) -> list[str] | None:
    """Return the Qdrant allowed_groups filter for a user's groups.

    If the user has 'all' in their groups, return None (no filter).
    Otherwise return their group list for MatchAny filtering.
    """
    if "all" in user_groups:
        return None
    return user_groups


def filter_access_level_for_role(role: str) -> str | None:
    """Determine what access_level filter to apply based on user role."""
    return get_qdrant_access_filter(role)
