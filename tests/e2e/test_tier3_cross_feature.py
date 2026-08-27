"""
Tier 3: Cross-Feature Combinations E2E Tests for ApexTender v2.0.
Verifies pairwise integration and cascading interactions across:
- Direct Storage Upload + LlamaParse Cloud Ingestion + Vector Search
- LlamaParse 429 + Client PDF.js Fallback + Ingestion + Groq SSE Stream
- Multi-document Upload + Cross-document Vector Query + Touch All
- Upload + keep_forever Protection + pg_cron Auto-Cleanup Dry-Run
- Multi-Tenant Complete Lifecycle Isolation
- Concurrent Multi-Query Execution under 300MB RAM Target
"""

import uuid
import asyncio
import datetime
import pytest
from typing import Dict, Any

from tests.fixtures.sample_rfps import DOD_CYBERSECURITY_RFP, HEALTHCARE_HIPAA_RFP, CLOUD_MIGRATION_RFP

def test_cross_upload_direct_storage_and_llamaparse_to_vector_search(client, supabase_service, primary_user):
    async def run():
        # 1. Direct storage upload
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/CyberDefense.pdf"
        file_bytes = DOD_CYBERSECURITY_RFP.encode("utf-8")
        
        up_res = await client.upload_file_to_storage("rfp-documents", path, file_bytes, "application/pdf", primary_user["token"])
        assert up_res.status_code == 200

        # 2. Insert document record in DB
        supabase_service.insert_document(doc_id, primary_user["id"], "CyberDefense.pdf", path, len(file_bytes))

        # 3. Trigger LlamaParse Edge Function
        proc_res = await client.trigger_process_document(doc_id, primary_user["token"])
        assert proc_res.status_code == 200
        assert proc_res.json()["status"] == "processed"

        # 4. Execute Vector Search via Query Stream
        status_code, sources, text, done, err = await client.query_stream(
            query="What are the FedRAMP High Authorization requirements in Section 2?",
            token=primary_user["token"]
        )
        assert status_code == 200
        assert len(sources) > 0
        assert any("FedRAMP" in s["snippet"] or "SEC-001" in s["snippet"] for s in sources)
        assert "FedRAMP" in text or "Authorization" in text
    asyncio.run(run())

def test_cross_upload_llamaparse_rate_limit_to_pdfjs_fallback_to_query_stream(
    client, supabase_service, llamaparse_service, primary_user
):
    async def run():
        # 1. Direct upload
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/Healthcare_RFP.pdf"
        file_bytes = HEALTHCARE_HIPAA_RFP.encode("utf-8")
        await client.upload_file_to_storage("rfp-documents", path, file_bytes, "application/pdf", primary_user["token"])
        supabase_service.insert_document(doc_id, primary_user["id"], "Healthcare_RFP.pdf", path, len(file_bytes))

        # 2. Simulate LlamaParse 429
        llamaparse_service.set_mode("429_rate_limit")
        proc_res = await client.trigger_process_document(doc_id, primary_user["token"])
        assert proc_res.json()["status"] == "awaiting_fallback_parse"
        assert supabase_service.documents[doc_id]["status"] == "awaiting_fallback_parse"

        # 3. Trigger Client-Side PDF.js Fallback Ingestion
        pages = [
            {"page_number": 1, "text": "## Page 1\n# Section 2.0 HIPAA & GDPR Framework\nContractor must execute Business Associate Agreement (BAA)."},
            {"page_number": 2, "text": "## Page 2\n# Section 3.0 Clinical SLAs\nVector search latency must be under 250ms P95."}
        ]
        fall_res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            pages=pages,
            parser_used="pdfjs_client_fallback"
        )
        assert fall_res.status_code == 200
        assert fall_res.json()["status"] == "processed"
        assert supabase_service.documents[doc_id]["status"] == "processed"

        # 4. Query RAG stream on fallback ingested chunks
        status_code, sources, text, done, err = await client.query_stream(
            query="What is the required Business Associate Agreement (BAA)?",
            token=primary_user["token"]
        )
        assert status_code == 200
        assert len(sources) > 0
        assert any("BAA" in s["snippet"] or "Business Associate" in s["snippet"] for s in sources)
        assert done["finish_reason"] == "stop"
        llamaparse_service.set_mode("success")
    asyncio.run(run())

def test_cross_upload_multiple_documents_multi_doc_query_and_touch_all(client, supabase_service, primary_user):
    async def run():
        # Upload 3 RFP documents with old timestamps
        old_time = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=15)
        doc1_id = str(uuid.uuid4())
        doc2_id = str(uuid.uuid4())
        doc3_id = str(uuid.uuid4())

        for doc_id, name, content in [
            (doc1_id, "DoD.pdf", DOD_CYBERSECURITY_RFP),
            (doc2_id, "Health.pdf", HEALTHCARE_HIPAA_RFP),
            (doc3_id, "Cloud.pdf", CLOUD_MIGRATION_RFP)
        ]:
            path = f"{primary_user['id']}/{doc_id}/{name}"
            supabase_service.storage_upload("rfp-documents", path, content.encode("utf-8"), "application/pdf", primary_user["id"])
            supabase_service.insert_document(doc_id, primary_user["id"], name, path, len(content), last_queried_at=old_time)
            await client.trigger_process_document(doc_id, primary_user["token"])

        # Execute query without document_ids filter (searches across all user's documents)
        status_code, sources, text, done, err = await client.query_stream(
            query="What are the SLA penalty and uptime requirements across the proposals?",
            token=primary_user["token"],
            match_count=10
        )
        assert status_code == 200
        assert len(sources) > 0
        
        # Verify touch_document_last_queried updated active documents
        matched_doc_ids = set(s["document_id"] for s in sources)
        for doc_id in matched_doc_ids:
            updated_time = datetime.datetime.fromisoformat(supabase_service.documents[doc_id]["last_queried_at"])
            if updated_time.tzinfo is None:
                updated_time = updated_time.replace(tzinfo=datetime.timezone.utc)
            assert updated_time > old_time
    asyncio.run(run())

def test_cross_upload_keep_forever_true_query_and_cron_run_preserves(client, supabase_service, primary_user):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/CriticalDoc.pdf"
        supabase_service.storage_upload("rfp-documents", path, DOD_CYBERSECURITY_RFP.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "CriticalDoc.pdf", path, 5000)
        await client.trigger_process_document(doc_id, primary_user["token"])

        # Set keep_forever = True
        await client.toggle_keep_forever(doc_id, keep_forever=True, token=primary_user["token"])

        # Advance simulated time to 45 days in future
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=45)
        
        # Trigger cleanup cron
        cron_res = await client.trigger_cleanup_cron(days=30, simulated_now_iso=future_time.isoformat())
        assert cron_res.status_code == 200
        
        # Document and chunks must still exist
        assert doc_id in supabase_service.documents
        assert len([c for c in supabase_service.document_chunks.values() if c["document_id"] == doc_id]) > 0

        # Query still works seamlessly
        status_code, sources, text, done, err = await client.query_stream(
            query="FedRAMP compliance",
            token=primary_user["token"]
        )
        assert status_code == 200
        assert len(sources) > 0
    asyncio.run(run())

def test_cross_upload_keep_forever_false_no_query_cron_run_deletes_and_cleans_storage(
    client, supabase_service, primary_user
):
    async def run():
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/EphemeralDoc.pdf"
        supabase_service.storage_upload("rfp-documents", path, b"data", "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "EphemeralDoc.pdf", path, 1024, keep_forever=False)
        await client.trigger_fallback_ingest(doc_id, primary_user["token"], extracted_text="Temporary text content")

        # Simulate 35 days pass without query
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=35)
        cron_res = await client.trigger_cleanup_cron(days=30, simulated_now_iso=future_time.isoformat())
        assert cron_res.status_code == 200
        data = cron_res.json()
        assert data["deleted_documents_count"] >= 1

        # Verify pruned
        assert doc_id not in supabase_service.documents
        assert len([c for c in supabase_service.document_chunks.values() if c["document_id"] == doc_id]) == 0
        assert path not in supabase_service.storage["rfp-documents"]
    asyncio.run(run())

def test_cross_multi_tenant_complete_isolation_upload_ingest_search_cron(
    client, supabase_service, primary_user, secondary_user
):
    async def run():
        # Tenant 1: DoD RFP
        doc1_id = str(uuid.uuid4())
        path1 = f"{primary_user['id']}/{doc1_id}/DoD.pdf"
        supabase_service.storage_upload("rfp-documents", path1, DOD_CYBERSECURITY_RFP.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc1_id, primary_user["id"], "DoD.pdf", path1, 5000, keep_forever=True)
        await client.trigger_process_document(doc1_id, primary_user["token"])

        # Tenant 2: Healthcare RFP
        doc2_id = str(uuid.uuid4())
        path2 = f"{secondary_user['id']}/{doc2_id}/Health.pdf"
        supabase_service.storage_upload("rfp-documents", path2, HEALTHCARE_HIPAA_RFP.encode("utf-8"), "application/pdf", secondary_user["id"])
        supabase_service.insert_document(doc2_id, secondary_user["id"], "Health.pdf", path2, 4000, keep_forever=False)
        await client.trigger_process_document(doc2_id, secondary_user["token"])

        # Tenant 1 searches for HIPAA (should find nothing because Tenant 1 has only DoD)
        st1, src1, txt1, done1, err1 = await client.query_stream(
            query="HIPAA Omnibus Rule Business Associate Agreement",
            token=primary_user["token"]
        )
        assert err1 is not None and err1.get("code") == "NO_CONTEXT_FOUND"

        # Tenant 2 searches for HIPAA (finds Health.pdf)
        st2, src2, txt2, done2, err2 = await client.query_stream(
            query="HIPAA Omnibus Rule Business Associate Agreement",
            token=secondary_user["token"]
        )
        assert st2 == 200
        assert len(src2) > 0
        assert src2[0]["document_id"] == doc2_id

        # Advance 40 days and run cleanup: Tenant 2 expired, Tenant 1 protected
        future_time = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=40)
        await client.trigger_cleanup_cron(days=30, simulated_now_iso=future_time.isoformat())

        assert doc1_id in supabase_service.documents
        assert doc2_id not in supabase_service.documents
    asyncio.run(run())

def test_cross_streaming_query_concurrent_retrieval_under_memory_limit(client, supabase_service, primary_user):
    async def run():
        # Ingest document
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/Doc.pdf"
        supabase_service.storage_upload("rfp-documents", path, DOD_CYBERSECURITY_RFP.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "Doc.pdf", path, 5000)
        await client.trigger_process_document(doc_id, primary_user["token"])

        # Execute 5 concurrent queries
        queries = [
            "What are the SLA terms?",
            "What are the FedRAMP compliance levels?",
            "What are the pricing phases?",
            "What are the penalties in section 3?",
            "What are the Top Secret personnel requirements?"
        ]
        tasks = [
            client.query_stream(query=q, token=primary_user["token"])
            for q in queries
        ]
        results = await asyncio.gather(*tasks)
        for st, src, txt, done, err in results:
            assert st == 200
            assert len(src) > 0
            assert done["finish_reason"] == "stop"

        # Check memory
        met_res = await client.get_system_metrics()
        assert met_res.json()["memory_rss_mb"] < 300.0
    asyncio.run(run())
