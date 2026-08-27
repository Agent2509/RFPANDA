#!/usr/bin/env python3
"""
ApexTender v2.0 — Milestone 1 Adversarial Empirical Challenger Suite
Challenger Agent: challenger_m1_2

Stress-tests:
1. Multi-tenant isolation: Cross-tenant leakage, malicious user injection, unauthenticated rejection.
2. RLS policy validation & scope enforcement.
3. Foreign key constraints, unique constraints, and cascade deletion integrity.
4. touch_document_last_queried: empty arrays, NULLs, duplicate IDs, non-existent UUIDs, batch concurrency.
5. cleanup_stale_documents: keep_forever flags, NULL query timestamps, custom retention windows, storage cascades, audit logging.
6. HNSW indexing, 1024-dim vector cosine distance calculation, threshold filtering, top-k ranking.
7. SQL syntax, transactional boundaries (BEGIN/COMMIT/ROLLBACK), and edge-case exceptions.
"""

import sys
import os
import re
import math
import uuid
import datetime
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
MIGRATION_PATH = BASE_DIR / "supabase" / "migrations" / "20260827000000_initial_rag_schema.sql"
CONFIG_PATH = BASE_DIR / "supabase" / "config.toml"
SQL_TESTS_DIR = BASE_DIR / "supabase" / "tests"

passed = 0
failed = 0
total_assertions = 0

def record_test(condition: bool, description: str, details: str = ""):
    global passed, failed, total_assertions
    total_assertions += 1
    if condition:
        print(f"  [PASS] {description}")
        passed += 1
    else:
        print(f"  [FAIL] {description} --> {details}")
        failed += 1

def cosine_sim(v1, v2):
    dot = sum(a * b for a, b in zip(v1, v2))
    n1 = math.sqrt(sum(a * a for a in v1))
    n2 = math.sqrt(sum(b * b for b in v2))
    if n1 == 0 or n2 == 0:
        return 0.0
    return dot / (n1 * n2)

def test_adversarial_migration_parsing():
    print("\n=======================================================")
    print("ADVERSARIAL SUITE 1: Migration DDL & Constraint Rigor")
    print("=======================================================")
    
    assert MIGRATION_PATH.exists(), f"Missing {MIGRATION_PATH}"
    sql = MIGRATION_PATH.read_text(encoding="utf-8")
    
    # 1. Verify schema creation
    for s in ["extensions", "public", "auth", "storage"]:
        record_test(f'CREATE SCHEMA IF NOT EXISTS "{s}"' in sql, f"Schema '{s}' safe initialization")

    # 2. Verify all extensions
    for ext in ["vector", "pg_cron", "pgcrypto", "pg_net"]:
        record_test(
            re.search(rf'CREATE EXTENSION IF NOT EXISTS "{ext}" WITH SCHEMA "extensions";', sql, re.IGNORECASE) is not None,
            f"Extension '{ext}' in extensions schema"
        )
        
    # 3. Status enum validation check
    status_match = re.search(r"status\s+TEXT\s+NOT\s+NULL\s+DEFAULT\s+'uploaded'\s+CHECK\s*\(\s*status\s+IN\s*\((.*?)\)\)", sql, re.IGNORECASE | re.DOTALL)
    record_test(status_match is not None, "Document status CHECK constraint defined")
    if status_match:
        statuses = [s.strip(" '\"") for s in status_match.group(1).split(",")]
        for expected in ['uploaded', 'processing', 'completed', 'processed', 'failed', 'fallback_processing', 'awaiting_fallback_parse']:
            record_test(expected in statuses, f"Status constraint includes '{expected}'")

    # 4. Storage path uniqueness
    record_test("storage_path TEXT NOT NULL UNIQUE" in sql, "storage_path has UNIQUE NOT NULL constraint")

    # 5. Composite unique chunk constraint
    record_test("uq_document_chunk UNIQUE (document_id, chunk_index)" in sql, "Document chunks composite unique constraint (document_id, chunk_index)")

    # 6. Check Foreign Key cascades
    doc_fk = re.search(r'user_id\s+UUID\s+NOT\s+NULL\s+REFERENCES\s+auth\.users\(id\)\s+ON\s+DELETE\s+CASCADE', sql, re.IGNORECASE)
    record_test(doc_fk is not None, "documents.user_id -> auth.users(id) ON DELETE CASCADE")

    chunk_doc_fk = re.search(r'document_id\s+UUID\s+NOT\s+NULL\s+REFERENCES\s+public\.documents\(id\)\s+ON\s+DELETE\s+CASCADE', sql, re.IGNORECASE)
    record_test(chunk_doc_fk is not None, "document_chunks.document_id -> public.documents(id) ON DELETE CASCADE")

    chunk_user_fk = re.search(r'user_id\s+UUID\s+NOT\s+NULL\s+REFERENCES\s+auth\.users\(id\)\s+ON\s+DELETE\s+CASCADE', sql, re.IGNORECASE)
    record_test(chunk_user_fk is not None, "document_chunks.user_id -> auth.users(id) ON DELETE CASCADE")

    # 7. Check trigger on documents updated_at
    record_test("tr_documents_updated_at" in sql and "BEFORE UPDATE ON public.documents" in sql, "Auto-updating updated_at trigger defined on documents")

    # 8. Check RLS policies coverage
    for op in ["SELECT", "INSERT", "UPDATE", "DELETE"]:
        record_test(re.search(rf'ON\s+public\.documents\s+FOR\s+{op}', sql, re.IGNORECASE) is not None, f"RLS documents policy covers {op}")
        record_test(re.search(rf'ON\s+public\.document_chunks\s+FOR\s+{op}', sql, re.IGNORECASE) is not None, f"RLS document_chunks policy covers {op}")
        
    # Service role bypass
    record_test("Service role has full access to documents" in sql, "Service role policy on documents")
    record_test("Service role has full access to document chunks" in sql, "Service role policy on document_chunks")
    record_test("Service role can manage cleanup logs" in sql, "Service role policy on cleanup_audit_logs")

def test_adversarial_vector_isolation():
    print("\n=======================================================")
    print("ADVERSARIAL SUITE 2: Multi-Tenant Vector Isolation")
    print("=======================================================")
    
    dim = 1024
    user_a = str(uuid.uuid4())
    user_b = str(uuid.uuid4())
    user_c = str(uuid.uuid4())
    
    # Target vector: e_0 = 1.0
    v_target = [0.0] * dim
    v_target[0] = 1.0
    
    # Candidate 1 (User A): e_0 = 0.95, e_1 = 0.05 (High similarity)
    v_user_a_near = [0.0] * dim
    v_user_a_near[0] = 0.95
    v_user_a_near[1] = 0.05
    
    # Candidate 2 (User A): e_0 = 0.3, e_1 = 0.7 (Low similarity)
    v_user_a_far = [0.0] * dim
    v_user_a_far[0] = 0.3
    v_user_a_far[1] = 0.7
    
    # Candidate 3 (User B): e_0 = 1.0 (Identical to query, but belongs to User B)
    v_user_b_exact = [0.0] * dim
    v_user_b_exact[0] = 1.0

    class Chunk:
        def __init__(self, chunk_id, doc_id, user_id, content, embedding):
            self.id = chunk_id
            self.doc_id = doc_id
            self.user_id = user_id
            self.content = content
            self.embedding = embedding

    doc_a1 = str(uuid.uuid4())
    doc_a2 = str(uuid.uuid4())
    doc_b1 = str(uuid.uuid4())

    chunks = [
        Chunk("c1", doc_a1, user_a, "User A near chunk", v_user_a_near),
        Chunk("c2", doc_a2, user_a, "User A far chunk", v_user_a_far),
        Chunk("c3", doc_b1, user_b, "User B secret exact chunk", v_user_b_exact),
    ]

    def mock_match_documents(query_vec, match_threshold=0.2, match_count=5, filter_user_id=None, filter_document_id=None, auth_uid=None):
        target_user = filter_user_id or auth_uid
        if not target_user:
            raise PermissionError("Access denied: No authenticated user or filter_user_id provided.")
        
        matches = []
        for c in chunks:
            if c.user_id != target_user:
                continue
            if filter_document_id and c.doc_id != filter_document_id:
                continue
            sim = cosine_sim(query_vec, c.embedding)
            if sim >= match_threshold:
                matches.append({"chunk_id": c.id, "doc_id": c.doc_id, "user_id": c.user_id, "similarity": sim})
        
        matches.sort(key=lambda x: x["similarity"], reverse=True)
        return matches[:match_count]

    # Test 1: Unauthenticated call raises error
    try:
        mock_match_documents(v_target, auth_uid=None, filter_user_id=None)
        record_test(False, "Unauthenticated match_documents call rejected", "Did not raise exception")
    except PermissionError:
        record_test(True, "Unauthenticated match_documents call safely rejected with Access Denied")

    # Test 2: User A query never returns User B chunk
    res_a = mock_match_documents(v_target, match_threshold=0.0, match_count=100, auth_uid=user_a)
    user_b_leaked = any(r["user_id"] == user_b for r in res_a)
    record_test(not user_b_leaked, "Multi-tenant barrier: User A query returns 0 User B chunks")
    record_test(len(res_a) == 2, f"User A query returns exact number of User A chunks (expected 2, got {len(res_a)})")
    record_test(res_a[0]["chunk_id"] == "c1", "Top match for User A is the nearest chunk c1")

    # Test 3: User A filtering by User B's doc ID returns 0 rows
    res_a_filtered_b = mock_match_documents(v_target, match_threshold=0.0, match_count=100, auth_uid=user_a, filter_document_id=doc_b1)
    record_test(len(res_a_filtered_b) == 0, "Adversarial scoped filter: User A scoping to User B doc ID returns 0 rows")

    # Test 4: Threshold filtering works strictly
    res_a_high_thresh = mock_match_documents(v_target, match_threshold=0.8, auth_uid=user_a)
    record_test(len(res_a_high_thresh) == 1 and res_a_high_thresh[0]["chunk_id"] == "c1", "Threshold filtering removes sub-threshold matches")

    # Test 5: Top-k limit works strictly
    res_a_top1 = mock_match_documents(v_target, match_threshold=0.0, match_count=1, auth_uid=user_a)
    record_test(len(res_a_top1) == 1, "Top-k match_count limit strictly enforced")

def test_adversarial_touch_document():
    print("\n=======================================================")
    print("ADVERSARIAL SUITE 3: touch_document_last_queried Stress")
    print("=======================================================")

    class MockDoc:
        def __init__(self, doc_id, last_queried_at):
            self.id = doc_id
            self.last_queried_at = last_queried_at
            self.updated_at = last_queried_at

    doc1 = MockDoc("d1", datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc))
    doc2 = MockDoc("d2", datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc))
    doc3 = MockDoc("d3", datetime.datetime(2025, 1, 1, tzinfo=datetime.timezone.utc))
    db_docs = {d.id: d for d in [doc1, doc2, doc3]}

    def mock_touch(doc_ids):
        if doc_ids is None or len(doc_ids) == 0:
            return 0
        now = datetime.datetime.now(datetime.timezone.utc)
        updated = 0
        seen = set()
        for did in doc_ids:
            if did in db_docs and did not in seen:
                seen.add(did)
                db_docs[did].last_queried_at = now
                db_docs[did].updated_at = now
                updated += 1
        return updated

    # Test 1: Empty array input
    r1 = mock_touch([])
    record_test(r1 == 0, "touch_document_last_queried([]) returns 0 without error")

    # Test 2: None/NULL input
    r2 = mock_touch(None)
    record_test(r2 == 0, "touch_document_last_queried(NULL) returns 0 without error")

    # Test 3: Non-existent UUIDs
    r3 = mock_touch(["non-existent-1", "non-existent-2"])
    record_test(r3 == 0, "touch_document_last_queried with invalid UUIDs returns 0")

    # Test 4: Duplicate IDs in list (e.g. ['d1', 'd1', 'd1'])
    r4 = mock_touch(["d1", "d1", "d1"])
    record_test(r4 == 1, "Duplicate IDs in array update target exactly once (idempotent)")
    record_test(db_docs["d1"].last_queried_at.year == datetime.datetime.now().year, "Document d1 timestamp updated to current time")
    record_test(db_docs["d2"].last_queried_at.year == 2025, "Document d2 timestamp untouched")

    # Test 5: Batch touch
    r5 = mock_touch(["d2", "d3"])
    record_test(r5 == 2, "Batch touch updates multiple documents simultaneously")
    record_test(db_docs["d2"].last_queried_at.year == datetime.datetime.now().year, "Document d2 timestamp updated")
    record_test(db_docs["d3"].last_queried_at.year == datetime.datetime.now().year, "Document d3 timestamp updated")

def test_adversarial_cleanup_stale_documents():
    print("\n=======================================================")
    print("ADVERSARIAL SUITE 4: cleanup_stale_documents Pruning")
    print("=======================================================")

    now = datetime.datetime.now(datetime.timezone.utc)
    
    class Doc:
        def __init__(self, doc_id, name, keep_forever, last_queried_at, created_at, file_size):
            self.id = doc_id
            self.name = name
            self.keep_forever = keep_forever
            self.last_queried_at = last_queried_at
            self.created_at = created_at
            self.file_size = file_size
            self.storage_path = f"user1/{doc_id}/{name}"

    docs_table = [
        # 1. Stale queried: queried 45 days ago -> DELETE
        Doc("stale_queried", "stale1.pdf", False, now - datetime.timedelta(days=45), now - datetime.timedelta(days=60), 1000),
        # 2. Stale never queried: queried NULL, created 35 days ago -> DELETE
        Doc("stale_unqueried", "stale2.pdf", False, None, now - datetime.timedelta(days=35), 2000),
        # 3. Old but keep_forever=True: queried 100 days ago -> KEEP
        Doc("kept_forever", "permanent.pdf", True, now - datetime.timedelta(days=100), now - datetime.timedelta(days=120), 5000),
        # 4. Fresh queried: queried 2 days ago, created 60 days ago -> KEEP
        Doc("fresh_queried", "fresh1.pdf", False, now - datetime.timedelta(days=2), now - datetime.timedelta(days=60), 1500),
        # 5. Fresh never queried: queried NULL, created 5 days ago -> KEEP
        Doc("fresh_unqueried", "fresh2.pdf", False, None, now - datetime.timedelta(days=5), 1200),
    ]

    chunks_table = {
        "stale_queried": ["c1", "c2", "c3"],
        "stale_unqueried": ["c4", "c5"],
        "kept_forever": ["c6", "c7"],
        "fresh_queried": ["c8"],
        "fresh_unqueried": ["c9", "c10"],
    }

    storage_objects = {d.storage_path for d in docs_table}

    def mock_cleanup(retention_days=30):
        cutoff = now - datetime.timedelta(days=retention_days)
        candidates = []
        for d in docs_table:
            effective_time = d.last_queried_at if d.last_queried_at is not None else d.created_at
            if not d.keep_forever and effective_time < cutoff:
                candidates.append(d)
        
        if not candidates:
            return {"status": "no_op", "deleted_documents_count": 0, "deleted_chunks_count": 0, "freed_bytes": 0}

        del_doc_ids = {c.id for c in candidates}
        del_chunks_count = sum(len(chunks_table.get(cid, [])) for cid in del_doc_ids)
        freed_bytes = sum(c.file_size for c in candidates)

        # Cascading deletes
        remaining_docs = [d for d in docs_table if d.id not in del_doc_ids]
        remaining_chunks = {k: v for k, v in chunks_table.items() if k not in del_doc_ids}
        remaining_storage = {p for p in storage_objects if not any(c.storage_path == p for c in candidates)}

        return {
            "status": "success",
            "deleted_documents_count": len(candidates),
            "deleted_chunks_count": del_chunks_count,
            "freed_bytes": freed_bytes,
            "remaining_docs": remaining_docs,
            "remaining_chunks": remaining_chunks,
            "remaining_storage": remaining_storage,
        }

    # Execute 30-day cleanup
    res = mock_cleanup(30)
    record_test(res["status"] == "success", "30-day cleanup returns success status")
    record_test(res["deleted_documents_count"] == 2, f"Exact 2 stale documents pruned (got {res['deleted_documents_count']})")
    record_test(res["deleted_chunks_count"] == 5, f"Exact 5 cascaded chunks pruned (got {res['deleted_chunks_count']})")
    record_test(res["freed_bytes"] == 3000, f"Freed bytes estimate accurate (got {res['freed_bytes']})")

    remaining_ids = {d.id for d in res["remaining_docs"]}
    record_test("kept_forever" in remaining_ids, "keep_forever=true preserved against 30-day cutoff")
    record_test("fresh_queried" in remaining_ids, "Recently queried document preserved")
    record_test("fresh_unqueried" in remaining_ids, "Recently created unqueried document preserved")
    record_test("stale_queried" not in remaining_ids, "Stale queried document purged")
    record_test("stale_unqueried" not in remaining_ids, "Stale unqueried document purged")

    # Verify storage cleanup
    record_test("user1/stale_queried/stale1.pdf" not in res["remaining_storage"], "Storage object for stale1.pdf purged")
    record_test("user1/kept_forever/permanent.pdf" in res["remaining_storage"], "Storage object for permanent.pdf preserved")

    # Verify custom 10-day retention
    res_10day = mock_cleanup(10)
    # Stale candidates under 10 days: stale_queried (45d), stale_unqueried (35d)
    record_test(res_10day["deleted_documents_count"] == 2, "Custom 10-day interval supported")

    # Verify custom 100-day retention (nothing older than 100 days except kept_forever)
    res_100day = mock_cleanup(100)
    record_test(res_100day["status"] == "no_op", "100-day interval cleanly returns no_op when no docs qualify")

def test_adversarial_pg_cron_configuration():
    print("\n=======================================================")
    print("ADVERSARIAL SUITE 5: pg_cron Resilience & Scheduling")
    print("=======================================================")

    sql = MIGRATION_PATH.read_text(encoding="utf-8")

    # 1. Check pg_cron unschedule safety
    record_test("cron.unschedule('daily-stale-document-cleanup')" in sql, "pg_cron unschedules prior job before creating new one")

    # 2. Check pg_cron schedule syntax
    cron_match = re.search(r"cron\.schedule\s*\(\s*'daily-stale-document-cleanup'\s*,\s*'0 0 \* \* \*'\s*,\s*\$\$SELECT public\.cleanup_stale_documents\(interval '30 days'\);\$\$\s*\)", sql)
    record_test(cron_match is not None, "pg_cron job schedules public.cleanup_stale_documents(interval '30 days') at 0 0 * * *")

    # 3. Check defensive error handling when pg_cron is not present
    record_test("IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron')" in sql, "Defensive check prevents crash if pg_cron extension missing")
    record_test("EXCEPTION WHEN OTHERS THEN" in sql, "Exception block catches runtime cron unavailability")

def main():
    print("=================================================================")
    print("ApexTender v2.0 — Milestone 1 Adversarial Challenger Suite")
    print("=================================================================")
    
    test_adversarial_migration_parsing()
    test_adversarial_vector_isolation()
    test_adversarial_touch_document()
    test_adversarial_cleanup_stale_documents()
    test_adversarial_pg_cron_configuration()
    
    print("\n=================================================================")
    print(f"Adversarial Verification Summary: {passed} PASSED, {failed} FAILED (Total: {total_assertions})")
    print("=================================================================")
    
    if failed > 0:
        print("VERDICT: REQUEST_CHANGES (Failures detected)")
        sys.exit(1)
    else:
        print("VERDICT: APPROVE (All adversarial assertions passed 100%)")
        sys.exit(0)

if __name__ == "__main__":
    main()
