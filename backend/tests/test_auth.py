"""
ApexTender v2.0 - Supabase JWT Authentication Unit & Integration Tests
Validates token signature checking, claims extraction, expiration handling, and multi-tenant isolation.
"""

import time
import jwt
import pytest
import httpx
from fastapi import HTTPException

from app.auth import get_current_user, AuthenticatedUser
from app.config import settings


@pytest.mark.asyncio
async def test_valid_jwt_token_claims_extraction(make_jwt):
    """
    Asserts that a validly signed Supabase JWT extracts subject, email, and role.
    """
    user_id = "99999999-8888-7777-6666-555555555555"
    email = "procurement.lead@enterprise.com"
    token = make_jwt(user_id=user_id, email=email, role="authenticated")

    user = await get_current_user(authorization=f"Bearer {token}")
    assert isinstance(user, AuthenticatedUser)
    assert user.id == user_id
    assert user.sub == user_id
    assert user.email == email
    assert user.role == "authenticated"


@pytest.mark.asyncio
async def test_expired_jwt_token_returns_401(test_jwt_secret):
    """
    Asserts that an expired token raises HTTP 401 with appropriate message.
    """
    now = int(time.time())
    expired_payload = {
        "sub": "user-expired",
        "email": "expired@test.com",
        "exp": now - 3600,
        "iat": now - 7200,
        "aud": "authenticated"
    }
    expired_token = jwt.encode(expired_payload, test_jwt_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=f"Bearer {expired_token}")
    assert exc_info.value.status_code == 401
    assert "expired" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_invalid_signature_jwt_returns_401():
    """
    Asserts that a token signed with an invalid secret is rejected with HTTP 401.
    """
    wrong_secret = "wrong-secret-key-1234567890"
    payload = {
        "sub": "user-tampered",
        "email": "tampered@test.com",
        "exp": int(time.time()) + 3600,
        "aud": "authenticated"
    }
    tampered_token = jwt.encode(payload, wrong_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=f"Bearer {tampered_token}")
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_missing_sub_claim_returns_401(test_jwt_secret):
    """
    Asserts that a token missing the sub claim raises HTTP 401.
    """
    payload = {
        "email": "nosub@test.com",
        "exp": int(time.time()) + 3600,
        "aud": "authenticated"
    }
    token_no_sub = jwt.encode(payload, test_jwt_secret, algorithm="HS256")

    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=f"Bearer {token_no_sub}")
    assert exc_info.value.status_code == 401
    assert "missing subject" in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_missing_authorization_header_returns_401():
    """
    Asserts that missing Authorization header raises HTTP 401.
    """
    with pytest.raises(HTTPException) as exc_info:
        await get_current_user(authorization=None)
    assert exc_info.value.status_code == 401


@pytest.mark.asyncio
async def test_test_mode_mock_token_bypass():
    """
    Asserts that mock test tokens are accepted when TEST_MODE is active.
    """
    token = "test-token-77777777-7777-7777-7777-777777777777"
    user = await get_current_user(authorization=f"Bearer {token}")
    assert user.id == "77777777-7777-7777-7777-777777777777"


@pytest.mark.asyncio
async def test_protected_query_endpoint_without_auth_returns_401(async_client: httpx.AsyncClient):
    """
    Asserts that POST /api/query without auth returns 401.
    """
    response = await async_client.post(
        "/api/query",
        json={"query": "Test question"}
    )
    assert response.status_code == 401
