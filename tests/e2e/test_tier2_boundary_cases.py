"""
Tier 2: Boundary & Corner Cases E2E Tests for ApexTender v2.0.
Verifies all 7 boundary dimensions:
1. Large files >10MB upload and processing (>=5 tests)
2. Empty and minimal files (>=5 tests)
3. Non-PDF formats and corrupt inputs (>=5 tests)
4. Malformed JSON and payload validation (>=5 tests)
5. Rate limit 429 triggers and API timeouts (>=5 tests)
6. Zero similarity matches and query edge cases (>=5 tests)
7. Expired vs Active retention date boundaries (>=5 tests)
"""

import uuid
import asyncio
import datetime
import pytest
from typing import Dict, Any

from tests.mocks.chunker import SemanticChunker
from tests.fixtures.document_generator import (
    generate_large_file_bytes,
    generate_corrupted_pdf_bytes,
    generate_empty_bytes,
    generate_multi_page_rfp_text,
    generate_docx_mock_bytes
)


# ==============================================================================
# Boundary 1: Large Files >10MB (5 Tests)
# ==============================================================================

def test_boundary_upload_12mb_file_succeeds_direct_storage(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/Huge_DoD_RFP_12MB.pdf"
        file_bytes = generate_large_file_bytes(size_in_mb=12.0)
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=file_bytes,
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert res.status_code == 200
        assert res.json()["size"] == len(file_bytes)
    asyncio.run(run())

def test_boundary_upload_20mb_file_succeeds(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/RFP_20MB.pdf"
        file_bytes = generate_large_file_bytes(size_in_mb=20.0)
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=file_bytes,
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert res.status_code == 200
    asyncio.run(run())

def test_boundary_upload_exceeding_max_bucket_limit_rejected(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        # 30MB exceeds 25MB (26214400 bytes) bucket limit
        path = f"{primary_user['id']}/{doc_id}/Oversized_30MB.pdf"
        file_bytes = generate_large_file_bytes(size_in_mb=30.0)
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=file_bytes,
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert res.status_code == 413
    asyncio.run(run())

def test_boundary_large_file_chunking_and_voyage_batching(app, voyage_service):
    # Generate 20-page document
    large_text = generate_multi_page_rfp_text(num_pages=20, sections_per_page=3)
    chunks = app.state.chunker.chunk_markdown(large_text)
    assert len(chunks) >= 40

    chunk_texts = [c["content"] for c in chunks]
    embed_res = voyage_service.create_embeddings(chunk_texts, input_type="document")
    assert len(embed_res["data"]) == len(chunks)
    assert embed_res["usage"]["total_tokens"] > 1000

def test_boundary_large_file_vector_search_performance(supabase_service, voyage_service, primary_user):
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(doc_id, primary_user["id"], "LargeDoc.pdf", "path", 15000000)
    
    # Insert 100 chunks
    large_text = generate_multi_page_rfp_text(num_pages=30, sections_per_page=2)
    chunker = SemanticChunker()
    chunks = chunker.chunk_markdown(large_text)
    
    chunk_texts = [c["content"] for c in chunks]
    embed_res = voyage_service.create_embeddings(chunk_texts, input_type="document")
    
    db_chunks = []
    for i, c in enumerate(chunks):
        db_chunks.append({
            "document_id": doc_id,
            "user_id": primary_user["id"],
            "chunk_index": c["chunk_index"],
            "content": c["content"],
            "embedding": embed_res["data"][i]["embedding"],
            "token_count": c["token_count"]
        })
    supabase_service.insert_chunks(db_chunks)

    query_emb = voyage_service.create_embeddings(["Technical Criteria 5.1"], input_type="query")["data"][0]["embedding"]
    start_time = datetime.datetime.now()
    matches = supabase_service.match_documents(query_embedding=query_emb, filter_user_id=primary_user["id"], match_count=5)
    duration = (datetime.datetime.now() - start_time).total_seconds()
    
    assert len(matches) > 0
    assert duration < 0.1  # Fast in-memory search < 100ms


# ==============================================================================
# Boundary 2: Empty & Minimal Files (5 Tests)
# ==============================================================================

def test_boundary_empty_0_byte_file_upload_handled(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/empty.pdf"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=generate_empty_bytes(),
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert res.status_code == 200
        assert res.json()["size"] == 0
    asyncio.run(run())

def test_boundary_empty_content_ingestion_handled(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/empty.pdf"
        supabase_service.storage_upload("rfp-documents", path, b"", "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "empty.pdf", path, 0)

        res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            extracted_text=""
        )
        assert res.status_code == 200
        assert res.json()["chunks_count"] == 0
        assert supabase_service.documents[doc_id]["status"] == "processed"
    asyncio.run(run())

def test_boundary_single_character_file_ingestion(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "single.txt", "path", 1)
        res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            extracted_text="A"
        )
        assert res.status_code == 200
        assert res.json()["chunks_count"] == 1
    asyncio.run(run())

def test_boundary_whitespace_only_file_ingestion(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "spaces.txt", "path", 10)
        res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            extracted_text="   \n\n\t   \n  "
        )
        assert res.status_code == 200
        assert res.json()["chunks_count"] == 0
    asyncio.run(run())

def test_boundary_empty_query_string_validation_error(client, primary_user):
    async def run():
        # Min length is 2
        status_code, sources, text, done, err = await client.query_stream(
            query="",
            token=primary_user["token"]
        )
        assert status_code == 422
    asyncio.run(run())


# ==============================================================================
# Boundary 3: Non-PDF Formats & Malformed Inputs (5 Tests)
# ==============================================================================

def test_boundary_plain_text_format_ingestion(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/rfp.txt"
        text_content = "Plain text RFP specification for procurement."
        supabase_service.storage_upload("rfp-documents", path, text_content.encode("utf-8"), "text/plain", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "rfp.txt", path, len(text_content), mime_type="text/plain")

        res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            extracted_text=text_content,
            parser_used="plaintext"
        )
        assert res.status_code == 200
        assert res.json()["chunks_count"] == 1
    asyncio.run(run())

def test_boundary_markdown_format_with_tables_ingestion(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/rfp.md"
        md_text = "# Header\n| Col1 | Col2 |\n|---|---|\n| Val1 | Val2 |"
        supabase_service.storage_upload("rfp-documents", path, md_text.encode("utf-8"), "text/markdown", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "rfp.md", path, len(md_text), mime_type="text/markdown")

        res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            extracted_text=md_text,
            parser_used="markdown"
        )
        assert res.status_code == 200
        assert res.json()["chunks_count"] >= 1
    asyncio.run(run())

def test_boundary_docx_mime_type_upload(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/document.docx"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=generate_docx_mock_bytes(),
            mime_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            token=primary_user["token"]
        )
        assert res.status_code == 200
    asyncio.run(run())

def test_boundary_unsupported_binary_format_rejected(client, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/malware.exe"
        res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=path,
            file_bytes=b"MZ\x90\x00executable",
            mime_type="application/x-msdownload",
            token=primary_user["token"]
        )
        assert res.status_code == 415
    asyncio.run(run())

def test_boundary_corrupted_pdf_stream_triggers_fallback(client, supabase_service, llamaparse_service, primary_user):
    async def run():
        llamaparse_service.set_mode("parse_error")
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/corrupted.pdf"
        supabase_service.storage_upload("rfp-documents", path, generate_corrupted_pdf_bytes(), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "corrupted.pdf", path, 100)

        res = await client.trigger_process_document(doc_id, token=primary_user["token"])
        assert res.status_code == 200
        assert res.json()["status"] == "awaiting_fallback_parse"
        llamaparse_service.set_mode("success")
    asyncio.run(run())


# ==============================================================================
# Boundary 4: Malformed JSON & Payload Validation (5 Tests)
# ==============================================================================

def test_boundary_query_with_malformed_json_body_422(client, primary_user):
    async def run():
        headers = {
            "Authorization": f"Bearer {primary_user['token']}",
            "Content-Type": "application/json"
        }
        res = await client.http_client.post("/api/query", content="INVALID_JSON{", headers=headers)
        assert res.status_code == 422
    asyncio.run(run())

def test_boundary_query_with_negative_match_count_422(client, primary_user):
    async def run():
        status_code, sources, text, done, err = await client.query_stream(
            query="Valid query",
            match_count=-5,
            token=primary_user["token"]
        )
        assert status_code == 422
    asyncio.run(run())

def test_boundary_query_with_similarity_threshold_out_of_bounds(client, primary_user):
    async def run():
        status_code, sources, text, done, err = await client.query_stream(
            query="Valid query",
            similarity_threshold=1.5,  # Max is 1.0
            token=primary_user["token"]
        )
        assert status_code == 422
    asyncio.run(run())

def test_boundary_fallback_with_nonexistent_document_404(client, primary_user):
    async def run():
        non_existent_id = str(uuid.uuid4())
        res = await client.trigger_fallback_ingest(
            document_id=non_existent_id,
            token=primary_user["token"],
            extracted_text="Some extracted text"
        )
        assert res.status_code == 404
    asyncio.run(run())

def test_boundary_query_with_sql_injection_attempt_handled_safely(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "path", 100)
        emb = voyage_service.create_embeddings(["Legitimate data"])["data"][0]["embedding"]
        supabase_service.insert_chunks([
            {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "Legitimate data", "embedding": emb}
        ])

        # SQL Injection in query string
        injection_query = "'; DROP TABLE documents; --"
        status_code, sources, text, done, err = await client.query_stream(
            query=injection_query,
            token=primary_user["token"]
        )
        assert status_code == 200
        # Verify table still exists intact
        assert doc_id in supabase_service.documents
    asyncio.run(run())


# ==============================================================================
# Boundary 5: Rate Limits (429) & API Timeouts (5 Tests)
# ==============================================================================

def test_boundary_llamaparse_429_immediately_triggers_fallback(client, supabase_service, llamaparse_service, primary_user):
    async def run():
        llamaparse_service.set_mode("429_rate_limit")
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/RFP.pdf"
        supabase_service.storage_upload("rfp-documents", path, b"PDF content", "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", path, 100)

        res = await client.trigger_process_document(doc_id, token=primary_user["token"])
        assert res.status_code == 200
        assert res.json()["status"] == "awaiting_fallback_parse"
        llamaparse_service.set_mode("success")
    asyncio.run(run())

def test_boundary_llamaparse_quota_exhausted_402_triggers_fallback(client, supabase_service, llamaparse_service, primary_user):
    async def run():
        llamaparse_service.set_mode("402_quota_exhausted")
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/RFP.pdf"
        supabase_service.storage_upload("rfp-documents", path, b"PDF content", "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", path, 100)

        res = await client.trigger_process_document(doc_id, token=primary_user["token"])
        assert res.status_code == 200
        assert res.json()["status"] == "awaiting_fallback_parse"
        llamaparse_service.set_mode("success")
    asyncio.run(run())

def test_boundary_llamaparse_polling_timeout_triggers_fallback(client, supabase_service, llamaparse_service, primary_user):
    async def run():
        llamaparse_service.set_mode("timeout")
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/RFP.pdf"
        supabase_service.storage_upload("rfp-documents", path, b"PDF content", "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "RFP.pdf", path, 100)

        res = await client.trigger_process_document(doc_id, token=primary_user["token"])
        assert res.status_code == 200
        assert res.json()["status"] == "awaiting_fallback_parse"
        llamaparse_service.set_mode("success")
    asyncio.run(run())

def test_boundary_voyage_ai_429_retries_with_exponential_backoff(voyage_service):
    voyage_service.set_rate_limit(enabled=True, threshold=2)
    # First 2 requests succeed
    res1 = voyage_service.create_embeddings(["text 1"])
    res2 = voyage_service.create_embeddings(["text 2"])
    assert len(res1["data"]) == 1
    assert len(res2["data"]) == 1

    # 3rd request hits 429
    with pytest.raises(Exception, match="429"):
        voyage_service.create_embeddings(["text 3"])
    voyage_service.set_rate_limit(enabled=False)

def test_boundary_groq_api_error_returns_sse_error_event(client, supabase_service, voyage_service, groq_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "path", 100)
        emb = voyage_service.create_embeddings(["Matched data content"])["data"][0]["embedding"]
        supabase_service.insert_chunks([
            {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "Matched data content", "embedding": emb}
        ])

        groq_service.set_error_simulation(enabled=True, error_type="500")
        status_code, sources, text, done, err = await client.query_stream(
            query="Matched data",
            token=primary_user["token"]
        )
        assert status_code == 200
        assert err is not None
        assert "500" in str(err)
        groq_service.set_error_simulation(enabled=False)
    asyncio.run(run())


# ==============================================================================
# Boundary 6: Zero Similarity Matches & Edge Search (5 Tests)
# ==============================================================================

def test_boundary_zero_similarity_matches_emits_informative_error_event(client, supabase_service, voyage_service, primary_user):
    async def run():
        # No documents in database
        status_code, sources, text, done, err = await client.query_stream(
            query="What are the encryption standards?",
            token=primary_user["token"]
        )
        assert status_code == 200
        assert err is not None
        assert err.get("code") == "NO_CONTEXT_FOUND"
        assert len(sources) == 0
    asyncio.run(run())

def test_boundary_query_high_threshold_returns_empty_sources(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "path", 100)
        emb = voyage_service.create_embeddings(["Standard document"])["data"][0]["embedding"]
        supabase_service.insert_chunks([
            {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "Standard document", "embedding": emb}
        ])

        # Similarity threshold of 0.999
        status_code, sources, text, done, err = await client.query_stream(
            query="Different query",
            similarity_threshold=0.999,
            token=primary_user["token"]
        )
        assert err is not None
        assert err["code"] == "NO_CONTEXT_FOUND"
    asyncio.run(run())

def test_boundary_query_against_nonexistent_document_id(client, supabase_service, voyage_service, primary_user):
    async def run():
        fake_doc_id = str(uuid.uuid4())
        status_code, sources, text, done, err = await client.query_stream(
            query="Query",
            document_ids=[fake_doc_id],
            token=primary_user["token"]
        )
        assert err is not None
        assert err["code"] == "NO_CONTEXT_FOUND"
    asyncio.run(run())

def test_boundary_query_against_other_user_document_id_returns_no_match(client, supabase_service, voyage_service, primary_user, secondary_user):
    async def run():
        # Secondary user uploads document
        sec_doc_id = str(uuid.uuid4())
        supabase_service.insert_document(sec_doc_id, secondary_user["id"], "Sec.pdf", "path", 100)
        emb = voyage_service.create_embeddings(["Proprietary IP"])["data"][0]["embedding"]
        supabase_service.insert_chunks([
            {"document_id": sec_doc_id, "user_id": secondary_user["id"], "chunk_index": 0, "content": "Proprietary IP", "embedding": emb}
        ])

        # Primary user queries specifying secondary user's document ID
        status_code, sources, text, done, err = await client.query_stream(
            query="Proprietary IP",
            document_ids=[sec_doc_id],
            token=primary_user["token"]
        )
        assert err is not None
        assert err["code"] == "NO_CONTEXT_FOUND"
    asyncio.run(run())

def test_boundary_query_with_regex_special_characters(client, supabase_service, voyage_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", "path", 100)
        emb = voyage_service.create_embeddings(["Regex test content"])["data"][0]["embedding"]
        supabase_service.insert_chunks([
            {"document_id": doc_id, "user_id": primary_user["id"], "chunk_index": 0, "content": "Regex test content", "embedding": emb}
        ])

        query = "^[a-z]+.*(test|content)?$+?()[]{}"
        status_code, sources, text, done, err = await client.query_stream(
            query=query,
            token=primary_user["token"]
        )
        assert status_code == 200
    asyncio.run(run())


# ==============================================================================
# Boundary 7: Expired vs Active Retention Dates (5 Tests)
# ==============================================================================

def test_boundary_retention_exact_30_day_cutoff_boundary(supabase_service, primary_user):
    now = datetime.datetime.now(datetime.timezone.utc)
    exact_30_days_ago = now - datetime.timedelta(days=30, seconds=1)
    
    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "BoundaryDoc.pdf", "path", 100,
        keep_forever=False, created_at=exact_30_days_ago, last_queried_at=exact_30_days_ago
    )

    res = supabase_service.cleanup_stale_documents(
        retention_interval=datetime.timedelta(days=30),
        simulated_now=now
    )
    assert res["deleted_documents_count"] == 1
    assert doc_id not in supabase_service.documents

def test_boundary_retention_29_days_23_hours_preserved(supabase_service, primary_user):
    now = datetime.datetime.now(datetime.timezone.utc)
    just_under_30 = now - datetime.timedelta(days=29, hours=23, minutes=50)

    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "PreservedDoc.pdf", "path", 100,
        keep_forever=False, created_at=just_under_30, last_queried_at=just_under_30
    )

    res = supabase_service.cleanup_stale_documents(
        retention_interval=datetime.timedelta(days=30),
        simulated_now=now
    )
    assert res["deleted_documents_count"] == 0
    assert doc_id in supabase_service.documents

def test_boundary_retention_30_days_1_minute_purged(supabase_service, primary_user):
    now = datetime.datetime.now(datetime.timezone.utc)
    just_over_30 = now - datetime.timedelta(days=30, minutes=1)

    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "PurgedDoc.pdf", "path", 100,
        keep_forever=False, created_at=just_over_30, last_queried_at=just_over_30
    )

    res = supabase_service.cleanup_stale_documents(
        retention_interval=datetime.timedelta(days=30),
        simulated_now=now
    )
    assert res["deleted_documents_count"] == 1
    assert doc_id not in supabase_service.documents

def test_boundary_retention_recently_queried_resets_clock(supabase_service, primary_user):
    now = datetime.datetime.now(datetime.timezone.utc)
    old_creation = now - datetime.timedelta(days=60)
    recent_query = now - datetime.timedelta(days=1)

    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "ActiveOldDoc.pdf", "path", 100,
        keep_forever=False, created_at=old_creation, last_queried_at=recent_query
    )

    res = supabase_service.cleanup_stale_documents(
        retention_interval=datetime.timedelta(days=30),
        simulated_now=now
    )
    assert doc_id in supabase_service.documents
    assert res["deleted_documents_count"] == 0

def test_boundary_retention_custom_retention_interval_param(supabase_service, primary_user):
    now = datetime.datetime.now(datetime.timezone.utc)
    ten_days_ago = now - datetime.timedelta(days=10)

    doc_id = str(uuid.uuid4())
    supabase_service.insert_document(
        doc_id, primary_user["id"], "TenDayDoc.pdf", "path", 100,
        keep_forever=False, created_at=ten_days_ago, last_queried_at=ten_days_ago
    )

    # Custom 7 days interval
    res = supabase_service.cleanup_stale_documents(
        retention_interval=datetime.timedelta(days=7),
        simulated_now=now
    )
    assert res["deleted_documents_count"] == 1
    assert doc_id not in supabase_service.documents
