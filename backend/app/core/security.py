"""
Security utilities for TriageNet.

Currently uses placeholder stubs — replace with real Azure AD B2C
JWT validation in production.
"""
from __future__ import annotations

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel


# ── Token scheme ──────────────────────────────────────────────────────────────
bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser(BaseModel):
    user_id: str
    username: str
    role: str           # "nurse" | "physician" | "admin"
    department_id: str


# ── Placeholder implementations ───────────────────────────────────────────────

def verify_token(token: str) -> dict:
    """
    Verify a JWT bearer token.
    
    TODO: Replace with azure-identity / msal JWT validation against
          Azure AD B2C tenant once deployed.
    """
    # Stub: accept any non-empty token
    if not token or token == "invalid":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return {
        "user_id": "usr-demo-001",
        "username": "nurse.demo",
        "role": "nurse",
        "department_id": "ED-01",
    }


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> CurrentUser:
    """
    FastAPI dependency — inject the authenticated user into any route.

    Usage:
        @router.get("/protected")
        async def protected(user: CurrentUser = Depends(get_current_user)):
            ...
    """
    # In development, return a mock nurse user when no token is supplied.
    if credentials is None:
        return CurrentUser(
            user_id="usr-demo-001",
            username="nurse.demo",
            role="nurse",
            department_id="ED-01",
        )

    payload = verify_token(credentials.credentials)
    return CurrentUser(**payload)


async def require_physician(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Restrict endpoint to physician role."""
    if user.role not in ("physician", "admin"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Physician access required.",
        )
    return user


async def require_admin(
    user: CurrentUser = Depends(get_current_user),
) -> CurrentUser:
    """Restrict endpoint to admin role."""
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access required.",
        )
    return user