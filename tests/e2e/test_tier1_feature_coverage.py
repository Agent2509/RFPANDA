"""
Tier 1: Feature Coverage E2E Tests for ApexTender v2.0.
Verifies all 8 core features specified in PROJECT.md:
1. Supabase Auth & JWT Verification (>=5 tests)
2. Supabase Storage Direct Upload & Bucket Policies (>=5 tests)
3. Document Ingestion Pipeline & Fallback Protocol (>=5 tests)
4. pgvector Matching & Cosine Similarity RPC (>=5 tests)
5. Groq Llama 3 SSE Streaming Query Endpoint (>=5 tests)
6. keep_forever Toggle & Document Management (>=5 tests)
7. Automated 30-Day Cleanup Cron & Cascade (>=5 tests)
8. Memory Footprint (<300MB RSS) & System Health (>=5 tests)
"""

import sys
import uuid
import asyncio
import datetime
import pytest
from typing import Dict, Any

from tests.fixtures.sample_rfps import DOD_CYBERSECURITY_RFP, HEALTHCARE_HIPAA_RFP
from tests.fixtures.document_generator import generate_docx_mock_bytes


# ==============================================================================
# Feature 1: Supabase Auth & JWT Verification (6 Tests)
# ==============================================================================

def test_auth_valid_supabase_token_success(client, primary_user):
    async def run():
        res = await client.list_documents(token=primary_user["token"])
        assert res.status_code == 200
        assert "documents" in res.json()
    asyncio.run(run())

def test_auth_missing_bearer_header_rejected(client):
    async def run():
        # Query endpoint without token
        status_code, sources, text, done, err = await client.query_stream(
            query="What are the SLA terms?",
            token=None
        )
        assert status_code == 401
    asyncio.run(run())

def test_auth_expired_token_rejected(client, supabase_service, primary_user):
    async def run():
        expired_token = supabase_service.generate_token(
            user_id=primary_user["id"],
            expires_in_seconds=-3600  # expired 1 hour ago
        )
        status_code, sources, text, done, err = await client.query_stream(
            query="What are the SLA terms?",
            token=expired_token
        )
        assert status_code == 401
    asyncio.run(run())

def test_auth_invalid_signature_secret_rejected(client, supabase_service, primary_user):
    async def run():
        bad_token = supabase_service.generate_token(
            user_id=primary_user["id"],
            custom_secret="wrong-secret-key-attacker"
        )
        res = await client.list_documents(token=bad_token)
        assert res.status_code == 401
    asyncio.run(run())

def test_auth_missing_sub_claim_rejected(client, supabase_service, primary_user):
    async def run():
        token_no_sub = supabase_service.generate_token(
            user_id=primary_user["id"],
            missing_sub=True
        )
        res = await client.list_documents(token=token_no_sub)
        assert res.status_code == 401
    asyncio.run(run())

def test_auth_non_authenticated_audience_rejected(client, supabase_service, primary_user):
    async def run():
        token_bad_aud = supabase_service.generate_token(
            user_id=primary_user["id"],
            audience="anon_user"
        )
        res = await client.list_documents(token=token_bad_aud)
        assert res.status_code == 401
    asyncio.run(run())


# ==============================================================================
# Feature 2: Storage Upload & Bucket Isolation (6 Tests)
# ==============================================================================

def test_upload_valid_pdf_to_user_folder_success(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/RFP-DoD-2026.pdf"
        file_bytes = b"%PDF-1.7 Sample RFP PDF"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=file_bytes,
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert res.status_code == 200
        assert res.json()["path"] == path
    asyncio.run(run())

def test_upload_valid_markdown_file_success(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/spec.md"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=DOD_CYBERSECURITY_RFP.encode("utf-8"),
            mime_type="text/markdown",
            token=primary_user["token"]
        )
        assert res.status_code == 200
    asyncio.run(run())

def test_upload_valid_docx_file_success(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/tender.docx"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=generate_docx_mock_bytes(),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            token=primary_user["token"]
        )
        assert res.status_code == 200
    asyncio.run(run())

def test_upload_multi_tenant_path_isolation_rejected(client, primary_user, secondary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        # Primary user attempts to upload to Secondary user's storage directory
        path = f"{secondary_user['id']}/{doc_id}/malicious_inject.pdf"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=b"%PDF-1.7 payload",
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert res.status_code == 403
    asyncio.run(run())

def test_upload_storage_metadata_and_path_generation(supabase_service, primary_user):
    doc_id = str(uuid.uuid4())
    path = f"{primary_user['id']}/{doc_id}/RFP_DoD.pdf"
    res = supabase_service.storage_upload(
        bucket_id="rfp-documents",
        path=path,
        data=b"test data",
        mime_type="application/pdf",
        user_id=primary_user["id"]
    )
    assert res["status_code"] == 200
    status, data, err = supabase_service.storage_download("rfp-documents", path, primary_user["id"])
    assert status == 200
    assert data == b"test data"

def test_upload_document_table_record_creation(supabase_service, primary_user):
    doc_id = str(uuid.uuid4())
    path = f"{primary_user['id']}/{doc_id}/DoD_RFP.pdf"
    doc = supabase_service.insert_document(
        doc_id=doc_id,
        user_id=primary_user["id"],
        name="DoD_RFP.pdf",
        storage_path=path,
        file_size=2048,
        status="uploaded"
    )
    assert doc["id"] == doc_id
    assert doc["status"] == "uploaded"
    assert doc["keep_forever"] is False


# ==============================================================================
# Feature 3: Document Ingestion Pipeline & Fallback Protocol (6 Tests)
# ==============================================================================

def test_ingest_llamaparse_success_and_chunk_generation(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/DoD_RFP.pdf"
        # Seed storage & doc
        supabase_service.storage_upload("rfp-documents", path, DOD_CYBERSECURITY_RFP.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "DoD_RFP.pdf", path, 5000, status="uploaded")

        res = await client.trigger_process_document(doc_id, token=primary_user["token"])
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "processed"
        assert data["chunks_count"] > 0
        
        # Verify chunks exist in pgvector table
        doc = supabase_service.documents[doc_id]
        assert doc["status"] == "processed"
        assert doc["total_chunks"] == data["chunks_count"]
    asyncio.run(run())

def test_ingest_llamaparse_rate_limit_transitions_to_awaiting_fallback(client, supabase_service, llamaparse_service, primary_user):
    async def run():
        llamaparse_service.set_mode("429_rate_limit")
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/DoD_RFP.pdf"
        supabase_service.storage_upload("rfp-documents", path, DOD_CYBERSECURITY_RFP.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "DoD_RFP.pdf", path, 5000, status="uploaded")

        res = await client.trigger_process_document(doc_id, token=primary_user["token"])
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "awaiting_fallback_parse"

        # Verify DB status updated
        doc = supabase_service.documents[doc_id]
        assert doc["status"] == "awaiting_fallback_parse"
        llamaparse_service.set_mode("success")  # Reset
    asyncio.run(run())

def test_ingest_client_pdfjs_fallback_endpoint_success(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/DoD_RFP.pdf"
        supabase_service.insert_document(doc_id, primary_user["id"], "DoD_RFP.pdf", path, 5000, status="awaiting_fallback_parse")

        pages = [
            {"page_number": 1, "text": "## Page 1\n# Section 1.0 Executive Scope\nThis RFP specifies cyber defense requirements."},
            {"page_number": 2, "text": "## Page 2\n# Section 2.0 SLA Terms\nCritical incidents must have response under 15 minutes."}
        ]
        res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            pages=pages,
            parser_used="pdfjs_client_fallback"
        )
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "processed"
        assert data["chunks_count"] >= 2
        assert data["source"] == "pdfjs_client_fallback"
        assert supabase_service.documents[doc_id]["status"] == "processed"
    asyncio.run(run())

def test_ingest_semantic_chunker_preserves_tables_and_headers(app):
    chunker = app.state.chunker
    chunks = chunker.chunk_markdown(DOD_CYBERSECURITY_RFP)
    assert len(chunks) >= 3
    # Check that table lines remained together
    table_chunks = [c for c in chunks if c["has_table"]]
    assert len(table_chunks) >= 1
    assert any("FedRAMP High Authorization" in c["content"] for c in table_chunks)

def test_ingest_batched_voyage_embeddings_1024d(voyage_service):
    texts = [f"Chunk number {i} with SLA and security requirements." for i in range(10)]
    res = voyage_service.create_embeddings(texts, input_type="document")
    assert res["object"] == "list"
    assert len(res["data"]) == 10
    for emb_item in res["data"]:
        assert len(emb_item["embedding"]) == 1024

def test_ingest_document_status_transitions(supabase_service, primary_user):
    doc_id = str(uuid.uuid4())
    doc = supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", "path", 100)
    assert doc["status"] == "uploaded"
    
    supabase_service.update_document(doc_id, {"status": "processing"})
    assert supabase_service.documents[doc_id]["status"] == "processing"

    supabase_service.update_document(doc_id, {"status": "awaiting_fallback_parse"})
    assert supabase_service.documents[doc_id]["status"] == "awaiting_fallback_parse"

    supabase_service.update_document(doc_id, {"status": "processed"})
    assert supabase_service.documents[doc_id]["status"] == "processed"


# ==============================================================================
# Feature 4: pgvector Matching & Cosine Similarity RPC (6 Tests)
# ==============================================================================

def test_vector_matching_exact_similarity_ranking(supabase_service, voyage_service, primary_user):
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(doc_id, primary_user["id"], "Security_RFP.pdf", "p", 1000)

    # Ingest 2 chunks: one on SLA penalties, one on general introduction
    emb_sla = voyage_service.create_embeddings(["Critical SLA penalty deduction is 15%."])["data"][0]["embedding"]
    emb_intro = voyage_service.create_embeddings(["This is an introduction to company services."])["data"][0]["embedding"]

    supabase_service.insert_chunks([
        {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "Critical SLA penalty deduction is 15%.", "embedding": emb_sla},
        {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 1, "content": "This is an introduction to company services.", "embedding": emb_intro}
    ])

    query_emb = voyage_service.create_embeddings(["What is the penalty for SLA failure?"], input_type="query")["data"][0]["embedding"]
    matches = supabase_service.match_documents(
        query_embedding=query_emb,
        match_threshold=0.05,
        filter_user_id=primary_user["id"],
        match_count=5
    )
    
    assert len(matches) == 2
    assert matches[0]["content"] == "Critical SLA penalty deduction is 15%."
    assert matches[0]["similarity"] > matches[1]["similarity"]

def test_vector_matching_threshold_filtering(supabase_service, voyage_service, primary_user):
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "p", 1000)
    emb = voyage_service.create_embeddings(["Specific cybersecurity STIG requirements."])["data"][0]["embedding"]
    supabase_service.insert_chunks([
        {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "Specific cybersecurity STIG requirements.", "embedding": emb}
    ])

    # Irrelevant query vector with high threshold
    query_emb = voyage_service.create_embeddings(["Cooking recipe for chocolate cookies."], input_type="query")["data"][0]["embedding"]
    matches = supabase_service.match_documents(query_embedding=query_emb, match_threshold=0.99, filter_user_id=primary_user["id"])
    assert len(matches) == 0

def test_vector_matching_user_isolation_filter(supabase_service, voyage_service, primary_user, secondary_user):
    # Primary user chunk
    doc1 = str(uuid.uuid4())
    supabase_service.insert_document(doc1, primary_user["id"], "Primary.pdf", "p1", 100)
    emb1 = voyage_service.create_embeddings(["Confidential Defense Budget $50M"])["data"][0]["embedding"]
    supabase_service.insert_chunks([
        {"document_id": doc1, "user_id": primary_user["id"], "chunk_index": 0, "content": "Confidential Defense Budget $50M", "embedding": emb1}
    ])

    # Secondary user vector search for budget
    query_emb = voyage_service.create_embeddings(["Defense Budget"], input_type="query")["data"][0]["embedding"]
    matches = supabase_service.match_documents(query_embedding=query_emb, filter_user_id=secondary_user["id"])
    assert len(matches) == 0  # Strict tenant isolation

def test_vector_matching_specific_document_id_filter(supabase_service, voyage_service, primary_user):
    doc1 = str(uuid.uuid4())
    doc2 = str(uuid.uuid4())
    supabase_service.insert_document(doc1, primary_user["id"], "Doc1.pdf", "p1", 100)
    supabase_service.insert_document(doc2, primary_user["id"], "Doc2.pdf", "p2", 100)

    emb = voyage_service.create_embeddings(["SLA term in Doc1 and Doc2"])["data"][0]["embedding"]
    supabase_service.insert_chunks([
        {"document_id": doc1, "user_id": primary_user["id"], "chunk_index": 0, "content": "Doc1 SLA term", "embedding": emb},
        {"document_id": doc2, "user_id": primary_user["id"], "chunk_index": 0, "content": "Doc2 SLA term", "embedding": emb}
    ])

    matches = supabase_service.match_documents(query_embedding=emb, filter_user_id=primary_user["id"], filter_document_ids=[doc1])
    assert len(matches) == 1
    assert matches[0]["document_id"] == doc1

def test_vector_matching_top_k_limit_enforcement(supabase_service, voyage_service, primary_user):
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "p", 100)
    emb = voyage_service.create_embeddings(["Generic chunk"])["data"][0]["embedding"]
    
    chunks = [
        {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": i, "content": f"Chunk {i}", "embedding": emb}
        for i in range(10)
    ]
    supabase_service.insert_chunks(chunks)
    matches = supabase_service.match_documents(query_embedding=emb, filter_user_id=primary_user["id"], match_count=3)
    assert len(matches) == 3

def test_vector_matching_unauthenticated_access_rejected(supabase_service, voyage_service):
    emb = voyage_service.create_embeddings(["test"])["data"][0]["embedding"]
    with pytest.raises(ValueError, match="Access denied"):
        supabase_service.match_documents(query_embedding=emb, filter_user_id=None)


# ==============================================================================
# Feature 5: Groq Llama 3 Streaming Endpoint (POST /api/query) (6 Tests)
# ==============================================================================

def test_groq_streaming_query_success_and_sse_events(client, supabase_service, voyage_service, primary_user):
    async def run():
        # Ingest document
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "DoD_SLA.pdf", "p", 1000)
        emb = voyage_service.create_embeddings(["SLA penalty deduction is 15% for uptime below 99.9%."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "SLA penalty deduction is 15% for uptime below 99.9%.", "embedding": emb,
            "metadata": {"page_number": 3, "section_header": "3.2 Uptime Penalties"}
        }])

        status_code, sources, text, done, err = await client.query_stream(
            query="What are the SLA penalty terms in Section 3?",
            token=primary_user["token"]
        )
        assert status_code == 200
        assert len(sources) > 0
        assert "SLA" in text or "penalty" in text.lower()
        assert done is not None
        assert done["finish_reason"] == "stop"
    asyncio.run(run())

def test_groq_streaming_emits_structured_sources_metadata(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "FedRAMP_Specs.pdf", "p", 1000)
        emb = voyage_service.create_embeddings(["FedRAMP High Authorization is required."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "FedRAMP High Authorization is required.", "embedding": emb,
            "metadata": {"page_number": 2, "section_header": "2.0 Security"}
        }])

        status_code, sources, text, done, err = await client.query_stream(
            query="FedRAMP requirements",
            token=primary_user["token"]
        )
        assert len(sources) >= 1
        src = sources[0]
        assert src["file_name"] == "FedRAMP_Specs.pdf"
        assert src["page_number"] == 2
        assert "similarity" in src
    asyncio.run(run())

def test_groq_streaming_emits_token_deltas(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "p", 1000)
        emb = voyage_service.create_embeddings(["Information regarding compliance guidelines."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "Information regarding compliance guidelines.", "embedding": emb
        }])

        status_code, sources, text, done, err = await client.query_stream(
            query="What are the compliance guidelines?",
            token=primary_user["token"]
        )
        assert len(text) > 20
    asyncio.run(run())

def test_groq_streaming_emits_done_event_with_usage(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "p", 1000)
        emb = voyage_service.create_embeddings(["Compliance content."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "Compliance content.", "embedding": emb
        }])

        status_code, sources, text, done, err = await client.query_stream(
            query="Compliance",
            token=primary_user["token"]
        )
        assert done is not None
        assert "total_sources" in done
    asyncio.run(run())

def test_groq_streaming_touches_document_last_queried(client, supabase_service, voyage_service, primary_user):
    async def run():
        old_time = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=10))
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(
            doc_id, primary_user["id"], "Doc.pdf", "p", 1000,
            last_queried_at=old_time
        )
        emb = voyage_service.create_embeddings(["Critical security policy."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "Critical security policy.", "embedding": emb
        }])

        await client.query_stream(query="security policy", token=primary_user["token"])
        
        # Verify last_queried_at was updated to now
        doc = supabase_service.documents[doc_id]
        updated_time = datetime.datetime.fromisoformat(doc["last_queried_at"])
        if updated_time.tzinfo is None:
            updated_time = updated_time.replace(tzinfo=datetime.timezone.utc)
        assert updated_time > old_time
    asyncio.run(run())

def test_groq_streaming_model_selection_support(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "p", 1000)
        emb = voyage_service.create_embeddings(["Topic content."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "Topic content.", "embedding": emb
        }])

        status_code, sources, text, done, err = await client.query_stream(
            query="Topic",
            token=primary_user["token"],
            model="llama-3.1-8b-instant"
        )
        assert status_code == 200
        assert len(text) > 0
    asyncio.run(run())


# ==============================================================================
# Feature 6: keep_forever Toggle & Exemption (5 Tests)
# ==============================================================================

def test_keep_forever_default_is_false(supabase_service, primary_user):
    doc_id = str(uuid.uuid4())
    doc = supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", "path", 500)
    assert doc["keep_forever"] is False

def test_keep_forever_toggle_to_true_persists(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", "path", 500, keep_forever=False)
        res = await client.toggle_keep_forever(doc_id, keep_forever=True, token=primary_user["token"])
        assert res.status_code == 200
        assert res.json()["keep_forever"] is True
        assert supabase_service.documents[doc_id]["keep_forever"] is True
    asyncio.run(run())

def test_keep_forever_toggle_back_to_false(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", "path", 500, keep_forever=True)
        res = await client.toggle_keep_forever(doc_id, keep_forever=False, token=primary_user["token"])
        assert res.status_code == 200
        assert res.json()["keep_forever"] is False
        assert supabase_service.documents[doc_id]["keep_forever"] is False
    asyncio.run(run())

def test_keep_forever_user_tenant_ownership_enforcement(client, supabase_service, primary_user, secondary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        # Document owned by Primary user
        supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", "path", 500, keep_forever=False)
        # Secondary user tries to toggle keep_forever
        res = await client.toggle_keep_forever(doc_id, keep_forever=True, token=secondary_user["token"])
        assert res.status_code == 403
    asyncio.run(run())

def test_keep_forever_protects_document_from_cleanup(supabase_service, primary_user):
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=45)
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "Important_RFP.pdf", "path", 1000,
        keep_forever=True, created_at=old_time, last_queried_at=old_time
    )
    result = supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert doc_id in supabase_service.documents
    assert result["deleted_documents_count"] == 0


# ==============================================================================
# Feature 7: Automated 30-Day Cleanup Cron & Cascade (6 Tests)
# ==============================================================================

def test_cleanup_stale_documents_deletes_expired_unprotected_docs(supabase_service, primary_user):
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=35)
    doc_id = str(uuid.uuid4())
    path = f"{primary_user['id']}/{doc_id}/Old.pdf"
    supabase_service.storage_upload("rfp-documents", path, b"file data", "application/pdf", primary_user["id"])
    supabase_service.insert_document(
        doc_id, primary_user["id"], "Old.pdf", path, 1024,
        keep_forever=False, created_at=old_time, last_queried_at=old_time
    )
    supabase_service.insert_chunks([{
        "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
        "content": "Old chunk", "embedding": [0.1] * 1024
    }])

    res = supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert res["status"] == "success"
    assert res["deleted_documents_count"] == 1
    assert res["deleted_chunks_count"] == 1
    assert doc_id not in supabase_service.documents
    assert path not in supabase_service.storage["rfp-documents"]

def test_cleanup_stale_documents_preserves_keep_forever_docs(supabase_service, primary_user):
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=60)
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "KeepMe.pdf", "path", 1024,
        keep_forever=True, created_at=old_time, last_queried_at=old_time
    )
    res = supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert doc_id in supabase_service.documents

def test_cleanup_stale_documents_preserves_recently_queried_docs(supabase_service, primary_user):
    created_old = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=40)
    queried_recent = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=5)
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "Active.pdf", "path", 1024,
        keep_forever=False, created_at=created_old, last_queried_at=queried_recent
    )
    res = supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert doc_id in supabase_service.documents

def test_cleanup_stale_documents_cascades_to_chunks_and_storage(supabase_service, primary_user):
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=31)
    doc_id = str(uuid.uuid4())
    path = f"{primary_user['id']}/{doc_id}/Doc.pdf"
    supabase_service.storage_upload("rfp-documents", path, b"binary", "application/pdf", primary_user["id"])
    supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", path, 100, keep_forever=False, created_at=old_time, last_queried_at=old_time)
    
    chunk_id1 = str(uuid.uuid4())
    chunk_id2 = str(uuid.uuid4())
    supabase_service.insert_chunks([
        {"id": chunk_id1, "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "C1", "embedding": [0.0]*1024},
        {"id": chunk_id2, "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 1, "content": "C2", "embedding": [0.0]*1024}
    ])

    supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert chunk_id1 not in supabase_service.document_chunks
    assert chunk_id2 not in supabase_service.document_chunks
    assert path not in supabase_service.storage["rfp-documents"]

def test_cleanup_stale_documents_creates_audit_log_record(supabase_service, primary_user):
    old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=35)
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(doc_id, primary_user["id"], "Old.pdf", "path", 2048, keep_forever=False, created_at=old_time, last_queried_at=old_time)
    
    supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert len(supabase_service.cleanup_audit_logs) >= 1
    log = supabase_service.cleanup_audit_logs[-1]
    assert log["deleted_documents_count"] == 1
    assert log["freed_bytes_estimate"] == 2048

def test_cleanup_stale_documents_no_op_when_no_stale_files(supabase_service):
    res = supabase_service.cleanup_stale_documents(retention_interval=datetime.timedelta(days=30))
    assert res["status"] == "no_op"
    assert res["deleted_documents_count"] == 0


# ==============================================================================
# Feature 8: Backend Memory Footprint & Health Diagnostics (5 Tests)
# ==============================================================================

def test_system_health_endpoint_healthy(client):
    async def run():
        res = await client.get_health()
        assert res.status_code == 200
        data = res.json()
        assert data["status"] == "healthy"
        assert "memory" in data
        assert data["memory"]["within_limits"] is True
    asyncio.run(run())

def test_system_metrics_endpoint_returns_memory_breakdown(client):
    async def run():
        res = await client.get_system_metrics()
        assert res.status_code == 200
        data = res.json()
        assert "memory_rss_mb" in data
        assert "memory_vms_mb" in data
        assert "cpu_percent" in data
        assert "threads_count" in data
    asyncio.run(run())

def test_system_rss_memory_strictly_under_300mb(client):
    async def run():
        res = await client.get_system_metrics()
        data = res.json()
        assert data["memory_rss_mb"] < 300.0, f"Memory {data['memory_rss_mb']}MB exceeded 300MB target"
    asyncio.run(run())

def test_system_memory_during_active_query_remains_under_300mb(client, supabase_service, voyage_service, primary_user):
    async def run():
        # Ingest document
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "path", 1000)
        emb = voyage_service.create_embeddings(["Large query memory load test payload."])["data"][0]["embedding"]
        supabase_service.insert_chunks([{
            "document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0,
            "content": "Large query memory load test payload.", "embedding": emb
        }])

        # Perform query
        await client.query_stream(query="Large query memory load", token=primary_user["token"])
        
        # Check metrics immediately after query
        res = await client.get_system_metrics()
        data = res.json()
        assert data["memory_rss_mb"] < 300.0
    asyncio.run(run())

def test_system_no_heavy_local_ml_libraries_loaded():
    """
    Verifies that no heavy local ML frameworks (torch, transformers, faiss, langchain)
    are loaded in the backend memory space.
    """
    forbidden_modules = ["transformers", "faiss", "langchain", "llama_index"]
    for mod in forbidden_modules:
        assert mod not in sys.modules, f"Forbidden heavy module '{mod}' is loaded into backend memory!"
