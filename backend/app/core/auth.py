"""Clerk-based authentication.

Validates Clerk-issued JWTs using JWKS (RS256).
Extracts user identity and role from token claims.
"""

from dataclasses import dataclass
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.core.config import get_settings

settings = get_settings()

# Bearer token extraction
bearer_scheme = HTTPBearer(auto_error=False)


@dataclass
class AuthenticatedUser:
    """Lightweight user representation from Clerk JWT claims."""

    id: str  # Clerk user ID (e.g., "user_2NNEq...")
    email: str | None = None
    full_name: str | None = None
    role: str = "student"
    image_url: str | None = None


class ClerkJWKSClient:
    """Fetches and caches Clerk's JWKS for RS256 token verification."""

    def __init__(self, jwks_url: str):
        self.jwks_url = jwks_url
        self._jwks_client = jwt.PyJWKClient(jwks_url, cache_keys=True, lifespan=3600)

    def get_signing_key(self, token: str):
        """Get the signing key for a given token from Clerk's JWKS."""
        return self._jwks_client.get_signing_key_from_jwt(token)


# Module-level JWKS client (lazy init)
_jwks_client: ClerkJWKSClient | None = None


def _get_jwks_client() -> ClerkJWKSClient:
    global _jwks_client
    if _jwks_client is None:
        if not settings.clerk_jwks_url:
            raise RuntimeError(
                "CLERK_JWKS_URL not configured. "
                "Set it to https://<your-clerk-domain>/.well-known/jwks.json"
            )
        _jwks_client = ClerkJWKSClient(settings.clerk_jwks_url)
    return _jwks_client


def _decode_clerk_token(token: str) -> dict:
    """Verify and decode a Clerk-issued JWT."""
    client = _get_jwks_client()

    try:
        signing_key = client.get_signing_key(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={
                "verify_exp": True,
                "verify_aud": False,  # Clerk doesn't always set aud
            },
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )


async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser:
    """Extract and validate the current user from a Clerk JWT.

    Reads role from Clerk's publicMetadata in the token claims.
    No database lookup required.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = _decode_clerk_token(credentials.credentials)

    # Extract user info from Clerk JWT claims
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token: missing subject",
        )

    # Clerk stores custom data in publicMetadata (accessible in session token
    # when you configure it in Clerk Dashboard → Sessions → Customize session token)
    metadata = payload.get("publicMetadata", payload.get("metadata", {})) or {}
    role = metadata.get("role", "student")

    # Some Clerk setups put user info in different claim locations
    email = (
        payload.get("email")
        or payload.get("primary_email_address")
        or metadata.get("email")
    )
    full_name = payload.get("name") or metadata.get("full_name")

    return AuthenticatedUser(
        id=user_id,
        email=email,
        full_name=full_name,
        role=role,
        image_url=payload.get("image_url"),
    )


async def get_current_user_optional(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
) -> AuthenticatedUser | None:
    """Optional auth — returns None if no token provided."""
    if credentials is None:
        return None
    try:
        return await get_current_user(credentials)
    except HTTPException:
        return None


def require_role(allowed_roles: list[str]):
    """Dependency factory: require user to have one of the allowed roles."""

    async def _check_role(
        current_user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    ) -> AuthenticatedUser:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' not authorized. Required: {allowed_roles}",
            )
        return current_user

    return _check_role


# ─── Type Aliases (same names as before — all routes work unchanged) ────────
CurrentUser = Annotated[AuthenticatedUser, Depends(get_current_user)]
OptionalUser = Annotated[AuthenticatedUser | None, Depends(get_current_user_optional)]
AdminUser = Annotated[AuthenticatedUser, Depends(require_role(["admin", "tutor"]))]
