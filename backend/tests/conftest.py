"""
ApexTender v2.0 - Pytest Test Fixtures and Mock Dependencies
"""

import sys
import os
from pathlib import Path
import time
import jwt
import pytest
import pytest_asyncio
import httpx
from typing import AsyncGenerator, Dict, Any, List

# Ensure backend/ is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Configure test environment variables before importing app modules
os.environ["ENVIRONMENT"] = "test"
os.environ["TEST_MODE"] = "true"
os.environ["SUPABASE_URL"] = "https://mock.supabase.co"
os.environ["SUPABASE_SERVICE_ROLE_KEY"] = "mock-service-role-key-test"
os.environ["SUPABASE_JWT_SECRET"] = "super-secret-test-jwt-key-for-apextender-tests"
os.environ["VOYAGE_API_KEY"] = "voyage-mock-api-key"
os.environ["GROQ_API_KEY"] = "groq-mock-api-key"

from app.config import settings
from app.main import create_app
from app.auth import AuthenticatedUser
from app.services.embedding import VoyageEmbeddingService
from app.services.vector_store import SupabaseVectorStore
from app.services.llm import GroqLLMService


@pytest.fixture(scope="session")
def test_jwt_secret() -> str:
    return settings.SUPABASE_JWT_SECRET


@pytest.fixture
def make_jwt(test_jwt_secret: str):
    """
    Factory fixture generating valid signed Supabase JWTs.
    """
    def _create_token(
        user_id: str = "11111111-2222-3333-4444-555555555555",
        email: str = "tester@apextender.test",
        role: str = "authenticated",
        expires_in: int = 3600,
        aud: str = "authenticated",
        extra_claims: Dict[str, Any] = None
    ) -> str:
        now = int(time.time())
        payload = {
            "sub": user_id,
            "email": email,
            "role": role,
            "aud": aud,
            "iat": now,
            "exp": now + expires_in,
            "user_metadata": {"full_name": "Test User"}
        }
        if extra_claims:
            payload.update(extra_claims)
        return jwt.encode(payload, test_jwt_secret, algorithm="HS256")
    return _create_token


@pytest.fixture
def valid_token(make_jwt) -> str:
    return make_jwt()


@pytest.fixture
def auth_headers(valid_token: str) -> Dict[str, str]:
    return {"Authorization": f"Bearer {valid_token}"}


@pytest.fixture
def mock_context_chunks() -> List[Dict[str, Any]]:
    return [
        {
            "chunk_id": "chunk-1111-2222",
            "document_id": "doc-aaaa-bbbb",
            "file_name": "DoD_Cyber_Security_RFP.pdf",
            "page_number": 4,
            "section_header": "4.1 Service Level Agreement Penalties",
            "similarity": 0.895,
            "content": "Section 4.1 SLA Penalty Terms: If monthly uptime drops below 99.9%, a 5% credit applies. Below 99.0%, a 15% credit applies.",
            "metadata": {"token_count": 45}
        },
        {
            "chunk_id": "chunk-3333-4444",
            "document_id": "doc-aaaa-bbbb",
            "file_name": "DoD_Cyber_Security_RFP.pdf",
            "page_number": 5,
            "section_header": "4.2 Incident Reporting Timelines",
            "similarity": 0.812,
            "content": "Section 4.2: Critical security incidents must be reported to the SOC within 60 minutes of detection.",
            "metadata": {"token_count": 38}
        }
    ]


@pytest_asyncio.fixture
async def async_client() -> AsyncGenerator[httpx.AsyncClient, None]:
    app = create_app()
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
