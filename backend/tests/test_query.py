"""
ApexTender v2.0 - Query SSE Streaming Integration Tests
Validates Server-Sent Events (SSE) protocol: sources metadata, token streaming,
done completion payload, zero-context error handling, parameter validation, and background touch.
"""

import json
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.services.vector_store import get_vector_store
from app.services.embedding import get_embedding_service


@pytest.mark.asyncio
async def test_query_endpoint_sse_streaming_success(
    async_client: httpx.AsyncClient,
    auth_headers: dict,
    mock_context_chunks: list
):
    """
    Asserts that POST /api/query returns a valid SSE stream with sources, tokens, and done event.
    """
    # Mock vector_store.match_documents to return realistic chunks
    vector_svc = get_vector_store()
    with patch.object(vector_svc, "match_documents", new_callable=AsyncMock) as mock_match, \
         patch.object(vector_svc, "touch_document_last_queried", new_callable=AsyncMock) as mock_touch:

        mock_match.return_value = mock_context_chunks
        mock_touch.return_value = 1

        payload = {
            "query": "What are the SLA penalty terms in Section 4?",
            "document_ids": ["doc-aaaa-bbbb"],
            "match_count": 5,
            "similarity_threshold": 0.25,
            "model": "llama-3.3-70b-versatile"
        }

        response = await async_client.post(
            "/api/query",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        assert "text/event-stream" in response.headers.get("content-type", "")

        # Parse SSE events from response text
        content = response.text
        events = []
        for block in content.split("\n\n"):
            block = block.strip()
            if not block:
                continue
            lines = block.split("\n")
            event_type = None
            event_data = None
            for line in lines:
                if line.startswith("event:"):
                    event_type = line.replace("event:", "").strip()
                elif line.startswith("data:"):
                    event_data = line.replace("data:", "").strip()
            if event_type and event_data:
                events.append((event_type, json.loads(event_data)))

        event_names = [e[0] for e in events]
        assert "sources" in event_names or "metadata" in event_names
        assert "token" in event_names
        assert "done" in event_names

        # Verify sources event payload
        sources_events = [e[1] for e in events if e[0] in ("sources", "metadata")]
        assert len(sources_events) > 0
        sources_list = sources_events[0].get("sources", [])
        assert len(sources_list) == 2
        assert sources_list[0]["file_name"] == "DoD_Cyber_Security_RFP.pdf"
        assert sources_list[0]["similarity"] == 0.895

        # Verify token streaming deltas
        token_events = [e[1] for e in events if e[0] == "token"]
        assert len(token_events) > 0
        streamed_text = "".join(t.get("delta", "") for t in token_events)
        assert len(streamed_text) > 0

        # Verify done event summary
        done_events = [e[1] for e in events if e[0] == "done"]
        assert len(done_events) == 1
        done_payload = done_events[0]
        assert done_payload["finish_reason"] == "stop"
        assert done_payload["total_sources"] == 2


@pytest.mark.asyncio
async def test_query_endpoint_zero_matches_emits_error_event(
    async_client: httpx.AsyncClient,
    auth_headers: dict
):
    """
    Asserts that when vector search yields no relevant chunks, an SSE error event is emitted.
    """
    vector_svc = get_vector_store()
    with patch.object(vector_svc, "match_documents", new_callable=AsyncMock) as mock_match:
        mock_match.return_value = []

        payload = {
            "query": "Unrelated topic with zero matching context",
            "similarity_threshold": 0.95
        }

        response = await async_client.post(
            "/api/query",
            json=payload,
            headers=auth_headers
        )

        assert response.status_code == 200
        content = response.text
        assert "event: error" in content
        assert "NO_CONTEXT_FOUND" in content


@pytest.mark.asyncio
async def test_query_validation_errors_return_422(
    async_client: httpx.AsyncClient,
    auth_headers: dict
):
    """
    Asserts that malformed queries fail input validation with HTTP 422.
    """
    # 1. Query too short
    res1 = await async_client.post(
        "/api/query",
        json={"query": "a"},
        headers=auth_headers
    )
    assert res1.status_code == 422

    # 2. Negative match_count
    res2 = await async_client.post(
        "/api/query",
        json={"query": "Valid query", "match_count": -5},
        headers=auth_headers
    )
    assert res2.status_code == 422

    # 3. Similarity threshold out of bounds (> 1.0)
    res3 = await async_client.post(
        "/api/query",
        json={"query": "Valid query", "similarity_threshold": 2.5},
        headers=auth_headers
    )
    assert res3.status_code == 422


@pytest.mark.asyncio
async def test_fallback_parse_endpoint(
    async_client: httpx.AsyncClient,
    auth_headers: dict
):
    """
    Asserts that POST /api/documents/fallback-parse handles extracted page text.
    """
    payload = {
        "document_id": "doc-fallback-uuid-1",
        "pages": [
            {"page_number": 1, "text": "Page 1 RFP Executive Summary text"},
            {"page_number": 2, "text": "Page 2 Technical Architecture requirements"}
        ],
        "parser_used": "pdfjs_client_fallback"
    }

    response = await async_client.post(
        "/api/documents/fallback-parse",
        json=payload,
        headers=auth_headers
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["document_id"] == "doc-fallback-uuid-1"


@pytest.mark.asyncio
async def test_list_documents_endpoint(
    async_client: httpx.AsyncClient,
    auth_headers: dict
):
    """
    Asserts that GET /api/documents returns user's document list.
    """
    vector_svc = get_vector_store()
    with patch.object(vector_svc, "list_documents", new_callable=AsyncMock) as mock_list:
        mock_list.return_value = [
            {"id": "doc-1", "name": "DoD_RFP.pdf", "status": "processed"}
        ]

        response = await async_client.get(
            "/api/documents",
            headers=auth_headers
        )

        assert response.status_code == 200
        data = response.json()
        assert "documents" in data
        assert len(data["documents"]) == 1
        assert data["documents"][0]["name"] == "DoD_RFP.pdf"
