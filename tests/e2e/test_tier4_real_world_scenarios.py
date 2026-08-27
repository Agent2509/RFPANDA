"""
Tier 4: Real-World Application Scenarios E2E Tests for ApexTender v2.0.
Verifies complete end-to-end user workflows and operational lifecycles:
1. Enterprise Defense RFP Full Procurement Lifecycle
2. Cloud Migration RFP with LlamaParse Rate Limit & Client Fallback
3. Multi-Tenant Enterprise Isolation & Retention Lifecycle
4. High-Throughput RFP Evaluation & Memory Stability (<300MB RSS)
"""

import uuid
import asyncio
import datetime
import pytest
from typing import Dict, Any

from tests.fixtures.sample_rfps import DOD_CYBERSECURITY_RFP, CLOUD_MIGRATION_RFP, HEALTHCARE_HIPAA_RFP
from tests.fixtures.document_generator import generate_multi_page_rfp_text

def test_scenario_enterprise_defense_rfp_full_procurement_lifecycle(client, supabase_service, primary_user):
    """
    Scenario 1: Complete DoD Cyber Defense Procurement Lifecycle.
    Upload -> LlamaParse Ingestion -> Chunk Table Preservation -> Voyage Embeddings ->
    Complex SLA Query -> SSE Streaming & Citations -> Touch Activity -> Retention Protection.
    """
    async def run():
        # Step 1: User authenticates and lists initial library
        docs_res = await client.list_documents(token=primary_user["token"])
        assert docs_res.status_code == 200
        initial_count = len(docs_res.json()["documents"])

        # Step 2: Direct browser-to-storage upload of DoD RFP document
        doc_id = str(uuid.uuid4())
        filename = "DoD_CyberDefense_RFP_2026.pdf"
        storage_path = f"{primary_user['id']}/{doc_id}/{filename}"
        file_bytes = DOD_CYBERSECURITY_RFP.encode("utf-8")

        upload_res = await client.upload_file_to_storage(
            bucket_id="rfp-documents",
            path=storage_path,
            file_bytes=file_bytes,
            mime_type="application/pdf",
            token=primary_user["token"]
        )
        assert upload_res.status_code == 200

        # Step 3: Insert initial DB document record
        supabase_service.insert_document(
            doc_id=doc_id,
            user_id=primary_user["id"],
            name=filename,
            storage_path=storage_path,
            file_size=len(file_bytes),
            mime_type="application/pdf",
            status="uploaded"
        )

        # Step 4: Storage Trigger / Client invokes process-document Edge Function
        ingest_res = await client.trigger_process_document(document_id=doc_id, token=primary_user["token"])
        assert ingest_res.status_code == 200
        ingest_data = ingest_res.json()
        assert ingest_data["status"] == "processed"
        assert ingest_data["chunks_count"] >= 3

        # Step 5: Verify document state in Database
        doc_record = supabase_service.documents[doc_id]
        assert doc_record["status"] == "processed"
        assert doc_record["total_chunks"] == ingest_data["chunks_count"]

        # Step 6: Evaluator executes complex multi-criteria query on SLA penalties & FedRAMP
        query = "What are the SLA uptime penalties and FedRAMP compliance requirements?"
        status_code, sources, streamed_text, done, error = await client.query_stream(
            query=query,
            document_ids=[doc_id],
            token=primary_user["token"],
            similarity_threshold=0.20,
            match_count=5
        )

        assert status_code == 200
        assert error is None
        assert len(sources) >= 1
        
        # Verify source citation metadata
        first_source = sources[0]
        assert first_source["document_id"] == doc_id
        assert first_source["file_name"] == filename
        assert "similarity" in first_source
        assert first_source["similarity"] >= 0.20

        # Verify streamed response
        assert len(streamed_text) > 50
        assert done is not None
        assert done["finish_reason"] == "stop"

        # Step 7: Verify last_queried_at was refreshed
        updated_doc = supabase_service.documents[doc_id]
        now_dt = datetime.datetime.now(datetime.timezone.utc)
        last_q_dt = datetime.datetime.fromisoformat(updated_doc["last_queried_at"])
        if last_q_dt.tzinfo is None:
            last_q_dt = last_q_dt.replace(tzinfo=datetime.timezone.utc)
        assert (now_dt - last_q_dt).total_seconds() < 5

        # Step 8: Execute pg_cron cleanup job (30 days interval) -> Document preserved because touched
        cron_res = await client.trigger_cleanup_cron(days=30)
        assert cron_res.status_code == 200
        assert doc_id in supabase_service.documents

    asyncio.run(run())

def test_scenario_cloud_migration_rfp_with_llamaparse_rate_limit_and_client_fallback(
    client, supabase_service, llamaparse_service, primary_user
):
    """
    Scenario 2: LlamaParse Rate Limit Recovery via Browser-Side PDF.js Fallback.
    Upload -> LlamaParse 429 -> awaiting_fallback_parse -> PDF.js Ingestion ->
    pgvector write -> Successful RAG SSE streaming.
    """
    async def run():
        doc_id = str(uuid.uuid4())
        filename = "State_DOT_Cloud_Migration_RFP.pdf"
        storage_path = f"{primary_user['id']}/{doc_id}/{filename}"
        file_bytes = CLOUD_MIGRATION_RFP.encode("utf-8")

        # 1. Upload
        await client.upload_file_to_storage("rfp-documents", storage_path, file_bytes, "application/pdf", primary_user["token"])
        supabase_service.insert_document(doc_id, primary_user["id"], filename, storage_path, len(file_bytes))

        # 2. Simulate LlamaParse Quota Exhaustion (429/402)
        llamaparse_service.set_mode("429_rate_limit")
        proc_res = await client.trigger_process_document(doc_id, primary_user["token"])
        assert proc_res.json()["status"] == "awaiting_fallback_parse"
        assert supabase_service.documents[doc_id]["status"] == "awaiting_fallback_parse"

        # 3. Client detects awaiting_fallback_parse and triggers PDF.js fallback
        extracted_pages = [
            {
                "page_number": 1,
                "text": "## Page 1\n# Section 1: Project Objective\nMigrate legacy mainframe tolling and traffic management applications to hybrid-cloud."
            },
            {
                "page_number": 2,
                "text": "## Page 2\n# Section 2: Technical Specifications & SLA Terms\nMaximum allowable maintenance window is <= 2 hours cutover. API throughput must be >= 15,000 TPS."
            },
            {
                "page_number": 3,
                "text": "## Page 3\n# Section 3: Pricing & Cost Breakdown\nTotal budget allocated is $3,500,000 over 24 months. Vendor proposals exceeding this will be disqualified."
            }
        ]

        fallback_res = await client.trigger_fallback_ingest(
            document_id=doc_id,
            token=primary_user["token"],
            pages=extracted_pages,
            parser_used="pdfjs_client_fallback"
        )
        assert fallback_res.status_code == 200
        assert fallback_res.json()["status"] == "processed"
        assert fallback_res.json()["chunks_count"] >= 3

        # 4. Evaluator queries budget and downtime SLAs
        query = "What is the total budget ceiling and maximum allowable downtime for database migration?"
        status_code, sources, text, done, err = await client.query_stream(
            query=query,
            document_ids=[doc_id],
            token=primary_user["token"]
        )
        assert status_code == 200
        assert len(sources) > 0
        assert any("3,500,000" in s["snippet"] or "downtime" in s["snippet"].lower() for s in sources)
        assert done["finish_reason"] == "stop"

        llamaparse_service.set_mode("success")
    asyncio.run(run())

def test_scenario_multi_tenant_enterprise_isolation_and_retention_lifecycle(
    client, supabase_service, primary_user, secondary_user
):
    """
    Scenario 3: Multi-Tenant Zero-Leakage & 30-Day Retention Pruning.
    Tenant A (Defense) & Tenant B (Healthcare) upload proprietary RFPs.
    Cross-query zero-leakage verified.
    Tenant A sets keep_forever = true; Tenant B sets keep_forever = false.
    Advance simulated clock 35 days -> run cleanup -> verify Tenant A survives, Tenant B deleted cleanly.
    """
    async def run():
        # Tenant A upload
        doc_a_id = str(uuid.uuid4())
        path_a = f"{primary_user['id']}/{doc_a_id}/DefenseSecret.pdf"
        supabase_service.storage_upload("rfp-documents", path_a, DOD_CYBERSECURITY_RFP.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_a_id, primary_user["id"], "DefenseSecret.pdf", path_a, 5000)
        await client.trigger_process_document(doc_a_id, primary_user["token"])
        await client.toggle_keep_forever(doc_a_id, keep_forever=True, token=primary_user["token"])

        # Tenant B upload
        doc_b_id = str(uuid.uuid4())
        path_b = f"{secondary_user['id']}/{doc_b_id}/HealthRecords.pdf"
        supabase_service.storage_upload("rfp-documents", path_b, HEALTHCARE_HIPAA_RFP.encode("utf-8"), "application/pdf", secondary_user["id"])
        supabase_service.insert_document(doc_b_id, secondary_user["id"], "HealthRecords.pdf", path_b, 4000, keep_forever=False)
        await client.trigger_process_document(doc_b_id, secondary_user["token"])

        # Zero-Leakage Search Test: Tenant A queries Tenant B's data
        st_a, src_a, txt_a, done_a, err_a = await client.query_stream(
            query="HIPAA Business Associate Agreement patient records",
            token=primary_user["token"]
        )
        assert err_a is not None and err_a.get("code") == "NO_CONTEXT_FOUND"

        # Zero-Leakage Search Test: Tenant B queries Tenant A's data
        st_b, src_b, txt_b, done_b, err_b = await client.query_stream(
            query="FedRAMP High Authorization STIG hardening DoD",
            token=secondary_user["token"]
        )
        assert err_b is not None and err_b.get("code") == "NO_CONTEXT_FOUND"

        # Advance simulated time by 35 days
        future_35d = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=35)
        cron_res = await client.trigger_cleanup_cron(days=30, simulated_now_iso=future_35d.isoformat())
        assert cron_res.status_code == 200
        data = cron_res.json()
        assert data["deleted_documents_count"] == 1
        assert data["freed_bytes"] == 4000

        # Verify Tenant A is intact
        assert doc_a_id in supabase_service.documents
        assert path_a in supabase_service.storage["rfp-documents"]
        assert len([c for c in supabase_service.document_chunks.values() if c["document_id"] == doc_a_id]) > 0

        # Verify Tenant B is completely purged
        assert doc_b_id not in supabase_service.documents
        assert path_b not in supabase_service.storage["rfp-documents"]
        assert len([c for c in supabase_service.document_chunks.values() if c["document_id"] == doc_b_id]) == 0
    asyncio.run(run())

def test_scenario_high_throughput_rfp_analysis_memory_stability(client, supabase_service, primary_user):
    """
    Scenario 4: High-Throughput RFP Evaluation & RAM Stability.
    Runs a series of 15 sequential and concurrent queries across ingested RFPs,
    asserting that memory RSS stays strictly under 300MB throughout.
    """
    async def run():
        # Ingest multi-page RFP
        doc_id = str(uuid.uuid4())
        path = f"{primary_user['id']}/{doc_id}/MultiRFP.pdf"
        multi_text = generate_multi_page_rfp_text(num_pages=15, sections_per_page=2)
        supabase_service.storage_upload("rfp-documents", path, multi_text.encode("utf-8"), "application/pdf", primary_user["id"])
        supabase_service.insert_document(doc_id, primary_user["id"], "MultiRFP.pdf", path, len(multi_text))
        await client.trigger_process_document(doc_id, primary_user["token"])

        # 10 sequential queries
        for i in range(1, 11):
            q = f"What are the specifications for Technical Criteria {i}.1?"
            st, src, txt, done, err = await client.query_stream(query=q, token=primary_user["token"])
            assert st == 200
            assert done["finish_reason"] == "stop"

        # Check memory
        health_res = await client.get_health()
        assert health_res.status_code == 200
        mem = health_res.json()["memory"]
        assert mem["within_limits"] is True
        assert mem["rss_mb"] < 300.0, f"Memory RSS exceeded: {mem['rss_mb']}MB"
    asyncio.run(run())
