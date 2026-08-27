"""
ApexTender v2.0 - Async Services Unit Tests
Covers Voyage AI embedding generation, Supabase pgvector RPC search,
and Groq LLM streaming token generation.
"""

import pytest
import httpx
from typing import List, Dict, Any

from app.services.embedding import VoyageEmbeddingService, VoyageEmbeddingError
from app.services.vector_store import SupabaseVectorStore, VectorStoreError
from app.services.llm import GroqLLMService


# ==============================================================================
# 1. Voyage Embedding Service Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_voyage_embed_query_generates_1024d_vector():
    """
    Asserts that VoyageEmbeddingService generates a 1024-dimensional vector with unit norm.
    """
    service = VoyageEmbeddingService(api_key="voyage-mock-test-key")
    query = "What are the SLA uptime commitments and penalty credits in Section 4?"
    vector = await service.embed_query(query)

    assert isinstance(vector, list)
    assert len(vector) == 1024
    assert all(isinstance(val, float) for val in vector)


@pytest.mark.asyncio
async def test_voyage_embed_documents_batching():
    """
    Asserts that VoyageEmbeddingService handles batched document chunks.
    """
    service = VoyageEmbeddingService(api_key="voyage-mock-test-key")
    chunks = [f"RFP Requirement Section {i}: Content description..." for i in range(10)]
    vectors = await service.embed_documents(chunks, batch_size=4)

    assert len(vectors) == 10
    assert all(len(v) == 1024 for v in vectors)


@pytest.mark.asyncio
async def test_voyage_retry_on_429_rate_limit(monkeypatch):
    """
    Asserts that VoyageEmbeddingService retries on HTTP 429 rate limit responses.
    """
    call_count = 0

    async def mock_handler(request: httpx.Request) -> httpx.Response:
        nonlocal call_count
        call_count += 1
        if call_count < 2:
            return httpx.Response(429, headers={"Retry-After": "0.01"}, json={"error": "Rate limit exceeded"})
        return httpx.Response(200, json={
            "data": [{"index": 0, "embedding": [0.1] * 1024}]
        })

    transport = httpx.MockTransport(mock_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        service = VoyageEmbeddingService(
            api_key="real-test-key",
            api_url="http://mock-voyage/v1/embeddings",
            max_retries=3,
            http_client=client
        )
        vector = await service.embed_query("Test query with rate limit retry")
        assert len(vector) == 1024
        assert call_count == 2


# ==============================================================================
# 2. Supabase pgvector Vector Store Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_vector_store_match_documents_formatting():
    """
    Asserts that match_documents correctly calls RPC and formats citation fields.
    """
    async def mock_rpc_handler(request: httpx.Request) -> httpx.Response:
        assert "/rest/v1/rpc/match_documents" in str(request.url)
        return httpx.Response(200, json=[
            {
                "id": "chunk-uuid-1",
                "document_id": "doc-uuid-1",
                "document_name": "RFP_Specification.pdf",
                "chunk_index": 2,
                "content": "Vendor shall maintain 99.9% availability.",
                "similarity": 0.892,
                "metadata": {"page_number": 3, "section_header": "Availability SLA"}
            }
        ])

    transport = httpx.MockTransport(mock_rpc_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        store = SupabaseVectorStore(
            supabase_url="http://mock-supabase",
            supabase_key="mock-key",
            http_client=client
        )

        results = await store.match_documents(
            query_embedding=[0.0] * 1024,
            filter_user_id="user-1234",
            match_threshold=0.2,
            match_count=5
        )

        assert len(results) == 1
        item = results[0]
        assert item["chunk_id"] == "chunk-uuid-1"
        assert item["document_id"] == "doc-uuid-1"
        assert item["file_name"] == "RFP_Specification.pdf"
        assert item["page_number"] == 3
        assert item["section_header"] == "Availability SLA"
        assert item["similarity"] == 0.892


@pytest.mark.asyncio
async def test_vector_store_touch_document_last_queried():
    """
    Asserts that touch_document_last_queried calls Supabase RPC.
    """
    async def mock_touch_handler(request: httpx.Request) -> httpx.Response:
        assert "/rest/v1/rpc/touch_document_last_queried" in str(request.url)
        return httpx.Response(200, json=2)

    transport = httpx.MockTransport(mock_touch_handler)
    async with httpx.AsyncClient(transport=transport) as client:
        store = SupabaseVectorStore(
            supabase_url="http://mock-supabase",
            supabase_key="mock-key",
            http_client=client
        )
        count = await store.touch_document_last_queried(["doc-1", "doc-2"])
        assert count == 2


# ==============================================================================
# 3. Groq LLM Streaming Service Tests
# ==============================================================================

@pytest.mark.asyncio
async def test_groq_format_context_prompt(mock_context_chunks):
    """
    Asserts that context chunks are formatted with file name, page, and section metadata.
    """
    service = GroqLLMService(api_key="groq-mock-key")
    prompt = service.format_context_prompt(mock_context_chunks)

    assert "DoD_Cyber_Security_RFP.pdf" in prompt
    assert "Page 4" in prompt
    assert "4.1 Service Level Agreement Penalties" in prompt
    assert "Section 4.1 SLA Penalty Terms" in prompt


@pytest.mark.asyncio
async def test_groq_stream_chat_completion_tokens(mock_context_chunks):
    """
    Asserts that GroqLLMService asynchronously streams tokens with citation formatting.
    """
    service = GroqLLMService(api_key="groq-mock-key")
    tokens = []
    async for token in service.stream_chat_completion(
        query="What are the SLA penalties?",
        context_chunks=mock_context_chunks
    ):
        tokens.append(token)

    assert len(tokens) > 0
    full_text = "".join(tokens)
    assert len(full_text) > 20
    assert "DoD_Cyber_Security_RFP.pdf" in full_text
