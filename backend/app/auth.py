"""
RFPANDA - Supabase JWT Authentication Middleware
Validates Supabase Bearer JWT tokens statelessly (HS256 signature verification)
when SUPABASE_JWT_SECRET is configured, or falls back to async non-blocking
Supabase auth client verification.
"""

import asyncio
import logging
from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel

from app.config import settings

logger = logging.getLogger("rfpanda.auth")

# Security scheme
security = HTTPBearer(auto_error=False)

# Singleton Supabase client for fallback verification
_supabase_auth_client: Optional[Any] = None


def get_supabase_auth_client():
    """Returns singleton Supabase client avoiding per-request allocation overhead."""
    global _supabase_auth_client
    if _supabase_auth_client is None:
        from supabase import create_client
        _supabase_auth_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
    return _supabase_auth_client


class AuthenticatedUser(BaseModel):
    """
    Authenticated user context extracted from validated Supabase JWT.
    """
    id: str
    email: str = ""
    role: str = "authenticated"
    metadata: Dict[str, Any] = {}

    @property
    def sub(self) -> str:
        """Alias for compatibility with dict-like sub property."""
        return self.id

    def __getitem__(self, item: str) -> Any:
        if item in ("id", "sub"):
            return self.id
        elif item == "email":
            return self.email
        elif item == "role":
            return self.role
        elif item in self.metadata:
            return self.metadata[item]
        raise KeyError(item)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(security),
    authorization: Optional[str] = Header(None)
) -> AuthenticatedUser:
    """
    FastAPI dependency validating the incoming Supabase JWT Bearer token.
    Extracts tenant UUID (`sub`), email, and role.
    """
    token: Optional[str] = None

    if isinstance(credentials, HTTPAuthorizationCredentials) and credentials.credentials:
        token = credentials.credentials
    elif authorization:
        if authorization.startswith("Bearer "):
            token = authorization.split(" ", 1)[1].strip()
        else:
            token = authorization.strip()

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing or invalid Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Test mode / Mock token fallback for local E2E simulation
    if settings.TEST_MODE and (token.startswith("test-token-") or token == "mock-token"):
        if token.startswith("test-token-"):
            user_id = token.replace("test-token-", "")
            return AuthenticatedUser(
                id=user_id,
                email=f"{user_id}@rfpanda.test",
                role="authenticated"
            )
        elif token == "mock-token":
            return AuthenticatedUser(
                id="00000000-0000-0000-0000-000000000001",
                email="test-mock@rfpanda.test",
                role="authenticated"
            )

    # Stateless HS256 JWT decoding if SUPABASE_JWT_SECRET is configured
    if settings.SUPABASE_JWT_SECRET:
        try:
            payload = jwt.decode(
                token,
                settings.SUPABASE_JWT_SECRET,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            sub = payload.get("sub")
            if not sub:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid token: Missing subject claim (sub)",
                    headers={"WWW-Authenticate": "Bearer"},
                )
            return AuthenticatedUser(
                id=str(sub),
                email=payload.get("email", ""),
                role=payload.get("role", "authenticated"),
                metadata=payload.get("user_metadata", {})
            )
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        except jwt.InvalidTokenError as exc:
            # Supabase projects on asymmetric signing keys (ES256/RS256) fail HS256
            # verification here. Fall through to Supabase API verification instead
            # of rejecting a potentially valid session token.
            logger.warning(
                f"HS256 verification failed ({str(exc)}); falling back to Supabase auth API"
            )

    # Fallback to Supabase API auth verification run non-blockingly on worker thread
    try:
        supabase = get_supabase_auth_client()
        user_response = await asyncio.to_thread(supabase.auth.get_user, token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: User not found or token expired",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = user_response.user
        return AuthenticatedUser(
            id=str(user.id),
            email=user.email or "",
            role=user.role or "authenticated",
            metadata=user.user_metadata or {}
        )

    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
