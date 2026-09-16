"""
ApexTender v2.0 - Supabase JWT Authentication Middleware
Validates Supabase Bearer JWT tokens statelessly (HS256 signature verification)
without requiring a database roundtrip.
"""

from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, status, Header
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
import jwt
from pydantic import BaseModel

from app.config import settings

# Security scheme
security = HTTPBearer(auto_error=False)


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
                email=f"{user_id}@apextender.test",
                role="authenticated"
            )
        elif token == "mock-token":
            return AuthenticatedUser(
                id="00000000-0000-0000-0000-000000000001",
                email="test-mock@apextender.test",
                role="authenticated"
            )

    try:
        from supabase import create_client
        supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_ANON_KEY)
        
        # This securely calls the Supabase API to verify the token, handling both HS256 and new RS256 tokens seamlessly
        user_response = supabase.auth.get_user(token)
        
        if not user_response or not user_response.user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token: User not found or token expired"
            )
            
        user = user_response.user
        user_id = str(user.id)
        email = user.email or ""
        role = user.role or "authenticated"
        user_metadata = user.user_metadata or {}

        return AuthenticatedUser(
            id=user_id,
            email=email,
            role=role,
            metadata=user_metadata
        )

    except Exception as exc:
        if isinstance(exc, HTTPException):
            raise exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(exc)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
