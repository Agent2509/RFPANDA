"""
Pytest Configuration and Fixtures for ApexTender v2.0 E2E Testing.
Provides mock service lifecycles, authenticated test tokens, and client instances.
"""

import pytest
import asyncio
from typing import Generator, Tuple, Dict, Any

from tests.mocks.mock_supabase import MockSupabaseService, JWT_SECRET
from tests.mocks.mock_voyage import MockVoyageService
from tests.mocks.mock_groq import MockGroqService
from tests.mocks.mock_llamaparse import MockLlamaParseService
from tests.mocks.mock_server_app import create_mock_app
from tests.test_client import ApexTenderTestClient

@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()

@pytest.fixture
def supabase_service() -> MockSupabaseService:
    return MockSupabaseService(jwt_secret=JWT_SECRET)

@pytest.fixture
def voyage_service() -> MockVoyageService:
    return MockVoyageService(dimension=1024, default_model="voyage-3-lite")

@pytest.fixture
def groq_service() -> MockGroqService:
    return MockGroqService(default_model="llama-3.3-70b-versatile")

@pytest.fixture
def llamaparse_service() -> MockLlamaParseService:
    return MockLlamaParseService()

@pytest.fixture
def app(supabase_service, voyage_service, groq_service, llamaparse_service):
    return create_mock_app(
        supabase_svc=supabase_service,
        voyage_svc=voyage_service,
        groq_svc=groq_service,
        llamaparse_svc=llamaparse_service
    )

@pytest.fixture
def client(app) -> ApexTenderTestClient:
    return ApexTenderTestClient(app=app)

@pytest.fixture
def primary_user(supabase_service) -> Dict[str, Any]:
    user_id = supabase_service.create_user(email="contractor@defensecorp.com")
    token = supabase_service.generate_token(user_id=user_id, email="contractor@defensecorp.com")
    return {"id": user_id, "email": "contractor@defensecorp.com", "token": token}

@pytest.fixture
def secondary_user(supabase_service) -> Dict[str, Any]:
    user_id = supabase_service.create_user(email="auditor@commercialinc.com")
    token = supabase_service.generate_token(user_id=user_id, email="auditor@commercialinc.com")
    return {"id": user_id, "email": "auditor@commercialinc.com", "token": token}
