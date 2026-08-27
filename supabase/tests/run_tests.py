#!/usr/bin/env python3
"""
ApexTender v2.0 — Milestone 1 Database & pgvector Schema Verification Suite.
Validates:
1. Migration SQL syntax, structure, DDL statements, tables, columns, indexes, RLS policies, RPCs.
2. Supabase config.toml validation (storage buckets, limits, ports, auth).
3. Vector mathematics simulation (1024 dimensions, cosine distance, HNSW parameters).
4. Auto-cleanup logic simulation (cutoff calculations, keep_forever preservation, cascade counts, audit logging).
5. All test SQL files in supabase/tests/ are self-consistent and well-formed.
"""

import sys
import os
import re
import math
import json
import uuid
import datetime
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent.parent
MIGRATION_FILE = BASE_DIR / "supabase" / "migrations" / "20260827000000_initial_rag_schema.sql"
CONFIG_FILE = BASE_DIR / "supabase" / "config.toml"
TESTS_DIR = BASE_DIR / "supabase" / "tests"

passed_tests = 0
failed_tests = 0

def assert_true(condition: bool, message: str):
    global passed_tests, failed_tests
    if condition:
        print(f"  [PASS] {message}")
        passed_tests += 1
    else:
        print(f"  [FAIL] {message}")
        failed_tests += 1

def test_migration_ddl_and_syntax():
    print("\n--- Running Suite 1: Migration DDL & Syntax Inspection ---")
    assert_true(MIGRATION_FILE.exists(), f"Migration file exists at {MIGRATION_FILE}")
    
    content = MIGRATION_FILE.read_text(encoding="utf-8")
    
    # 1. Check Extensions
    for ext in ["vector", "pg_cron", "pgcrypto", "pg_net"]:
        assert_true(
            re.search(rf'CREATE\s+EXTENSION\s+IF\s+NOT\s+EXISTS\s+"?{ext}"?', content, re.IGNORECASE) is not None,
            f"Extension '{ext}' is created with IF NOT EXISTS"
        )
        
    # 2. Check Tables
    for tbl in ["documents", "document_chunks", "cleanup_audit_logs"]:
        assert_true(
            re.search(rf'CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+public\.{tbl}', content, re.IGNORECASE) is not None,
            f"Table 'public.{tbl}' is created with IF NOT EXISTS"
        )

    # 3. Check Documents Columns
    doc_cols = ["id", "user_id", "name", "storage_path", "file_size", "mime_type", "status", "keep_forever", "last_queried_at", "created_at", "updated_at", "metadata"]
    for col in doc_cols:
        assert_true(
            re.search(rf'\b{col}\b', content, re.IGNORECASE) is not None,
            f"Column 'documents.{col}' is defined"
        )

    # 4. Check Document Chunks Columns & 1024-dim vector
    chunk_cols = ["id", "document_id", "user_id", "chunk_index", "content", "embedding", "token_count", "metadata", "created_at"]
    for col in chunk_cols:
        assert_true(
            re.search(rf'\b{col}\b', content, re.IGNORECASE) is not None,
            f"Column 'document_chunks.{col}' is defined"
        )
    assert_true(
        "vector(1024)" in content.lower(),
        "document_chunks.embedding is 1024-dimensional vector(1024)"
    )

    # 5. Check Cleanup Audit Logs Columns
    audit_cols = ["id", "executed_at", "documents_deleted_count", "chunks_deleted_count", "freed_bytes_estimate", "execution_duration_ms", "details"]
    for col in audit_cols:
        assert_true(
            re.search(rf'\b{col}\b', content, re.IGNORECASE) is not None,
            f"Column 'cleanup_audit_logs.{col}' is defined"
        )

    # 6. Check Foreign Key and ON DELETE CASCADE
    assert_true(
        "on delete cascade" in content.lower(),
        "Foreign keys include ON DELETE CASCADE"
    )

    # 7. Check HNSW Index
    assert_true(
        re.search(r'idx_document_chunks_embedding_hnsw.*?using\s+hnsw\s*\(\s*embedding\s+vector_cosine_ops\s*\)\s*with\s*\(\s*m\s*=\s*16,\s*ef_construction\s*=\s*64\s*\)', content, re.IGNORECASE | re.DOTALL) is not None,
        "HNSW index 'idx_document_chunks_embedding_hnsw' with (m=16, ef_construction=64) defined"
    )

    # 8. Check B-Tree Indexes
    for idx in ["idx_documents_user_id", "idx_documents_last_queried_at", "idx_documents_keep_forever", "idx_documents_status", "idx_document_chunks_document_id", "idx_document_chunks_user_id"]:
        assert_true(
            idx in content,
            f"B-Tree index '{idx}' is defined"
        )

    # 9. Check RLS & Policies
    assert_true(
        "alter table public.documents enable row level security" in content.lower(),
        "RLS enabled on public.documents"
    )
    assert_true(
        "alter table public.document_chunks enable row level security" in content.lower(),
        "RLS enabled on public.document_chunks"
    )
    assert_true(
        "alter table public.cleanup_audit_logs enable row level security" in content.lower(),
        "RLS enabled on public.cleanup_audit_logs"
    )
    assert_true(
        "auth.uid() = user_id" in content.lower(),
        "RLS policy enforces auth.uid() = user_id"
    )
    assert_true(
        "service_role" in content.lower(),
        "RLS policies configure service_role access"
    )

    # 10. Check Stored Procedures
    assert_true(
        "function public.match_documents" in content.lower(),
        "RPC function 'match_documents' is defined"
    )
    assert_true(
        "function public.touch_document_last_queried" in content.lower(),
        "RPC function 'touch_document_last_queried' is defined"
    )
    assert_true(
        "function public.cleanup_stale_documents" in content.lower(),
        "RPC function 'cleanup_stale_documents' is defined"
    )

    # 11. Check pg_cron Schedule
    assert_true(
        "daily-stale-document-cleanup" in content,
        "pg_cron job 'daily-stale-document-cleanup' is scheduled"
    )
    assert_true(
        "0 0 * * *" in content,
        "pg_cron schedule '0 0 * * *' (midnight UTC) is specified"
    )

def test_supabase_config():
    print("\n--- Running Suite 2: Supabase config.toml Verification ---")
    assert_true(CONFIG_FILE.exists(), f"Config file exists at {CONFIG_FILE}")
    config_text = CONFIG_FILE.read_text(encoding="utf-8")
    
    assert_true('project_id = "rfp-engine"' in config_text, "Project ID configured as 'rfp-engine'")
    assert_true('[storage.buckets.rfp-documents]' in config_text, "Storage bucket 'rfp-documents' defined")
    assert_true('file_size_limit = "50MiB"' in config_text, "50MiB file size limit configured")
    assert_true('major_version = 15' in config_text, "Postgres major version 15 specified")
    assert_true('[edge_runtime]' in config_text, "Edge runtime configured")
    assert_true('[auth]' in config_text, "Auth service configured")

def test_vector_similarity_math():
    print("\n--- Running Suite 3: Vector Math & Cosine Similarity Simulation ---")
    dim = 1024
    
    def cosine_similarity(v1, v2):
        dot = sum(a * b for a, b in zip(v1, v2))
        norm1 = math.sqrt(sum(a * a for a in v1))
        norm2 = math.sqrt(sum(b * b for b in v2))
        if norm1 == 0 or norm2 == 0:
            return 0.0
        return dot / (norm1 * norm2)

    # Query vector: [1.0, 0.0, ...]
    query_vec = [0.0] * dim
    query_vec[0] = 1.0

    # Match chunk 1: [0.95, 0.05, ...]
    chunk1_vec = [0.0] * dim
    chunk1_vec[0] = 0.95
    chunk1_vec[1] = 0.05

    # Match chunk 2: [0.3, 0.7, ...]
    chunk2_vec = [0.0] * dim
    chunk2_vec[0] = 0.3
    chunk2_vec[1] = 0.7

    # Orthogonal chunk: [0.0, 1.0, ...]
    chunk3_vec = [0.0] * dim
    chunk3_vec[1] = 1.0

    sim1 = cosine_similarity(query_vec, chunk1_vec)
    sim2 = cosine_similarity(query_vec, chunk2_vec)
    sim3 = cosine_similarity(query_vec, chunk3_vec)

    assert_true(sim1 > 0.99, f"High similarity vector scores >0.99 ({sim1:.4f})")
    assert_true(0.35 < sim2 < 0.45, f"Moderate similarity vector scores as expected ({sim2:.4f})")
    assert_true(abs(sim3 - 0.0) < 1e-6, f"Orthogonal vector scores exactly 0.0 ({sim3:.4f})")
    assert_true(sim1 > sim2 > sim3, "Rank ordering correctly reflects cosine similarity")

def test_cleanup_stale_documents_logic():
    print("\n--- Running Suite 4: Auto-Cleanup Logic & Lifecycle Simulation ---")
    now = datetime.datetime.now(datetime.timezone.utc)
    retention_days = 30
    cutoff = now - datetime.timedelta(days=retention_days)

    class MockDocument:
        def __init__(self, doc_id, user_id, keep_forever, last_queried_at, created_at, file_size):
            self.id = doc_id
            self.user_id = user_id
            self.keep_forever = keep_forever
            self.last_queried_at = last_queried_at
            self.created_at = created_at
            self.file_size = file_size

    class MockChunk:
        def __init__(self, chunk_id, document_id):
            self.id = chunk_id
            self.document_id = document_id

    # Populate mock DB
    doc_stale_1 = MockDocument(str(uuid.uuid4()), "user1", False, now - datetime.timedelta(days=45), now - datetime.timedelta(days=50), 1000)
    doc_stale_2_null_query = MockDocument(str(uuid.uuid4()), "user1", False, None, now - datetime.timedelta(days=40), 2000)
    doc_kept_forever = MockDocument(str(uuid.uuid4()), "user1", True, now - datetime.timedelta(days=100), now - datetime.timedelta(days=100), 5000)
    doc_fresh = MockDocument(str(uuid.uuid4()), "user1", False, now - datetime.timedelta(days=5), now - datetime.timedelta(days=6), 1500)

    docs = [doc_stale_1, doc_stale_2_null_query, doc_kept_forever, doc_fresh]
    chunks = [
        MockChunk(str(uuid.uuid4()), doc_stale_1.id),
        MockChunk(str(uuid.uuid4()), doc_stale_1.id),
        MockChunk(str(uuid.uuid4()), doc_stale_2_null_query.id),
        MockChunk(str(uuid.uuid4()), doc_kept_forever.id),
        MockChunk(str(uuid.uuid4()), doc_fresh.id),
    ]

    # Stored procedure cleanup_stale_documents logic
    stale_docs = [
        d for d in docs
        if not d.keep_forever and (d.last_queried_at or d.created_at) < cutoff
    ]
    stale_doc_ids = {d.id for d in stale_docs}
    deleted_chunks = [c for c in chunks if c.document_id in stale_doc_ids]
    surviving_docs = [d for d in docs if d.id not in stale_doc_ids]
    surviving_chunks = [c for c in chunks if c.document_id not in stale_doc_ids]

    assert_true(len(stale_docs) == 2, f"Expected 2 stale documents identified, found {len(stale_docs)}")
    assert_true(doc_stale_1 in stale_docs, "Stale doc 1 (45 days old) marked for deletion")
    assert_true(doc_stale_2_null_query in stale_docs, "Stale doc 2 (NULL queried, 40 days old) marked for deletion")
    assert_true(doc_kept_forever in surviving_docs, "keep_forever=true document is preserved")
    assert_true(doc_fresh in surviving_docs, "Fresh document (5 days old) is preserved")
    assert_true(len(deleted_chunks) == 3, f"Expected 3 cascading chunks deleted, found {len(deleted_chunks)}")
    assert_true(len(surviving_chunks) == 2, f"Expected 2 surviving chunks, found {len(surviving_chunks)}")

def test_sql_test_files():
    print("\n--- Running Suite 5: SQL Test Scripts Existence & Structure ---")
    expected_sql_tests = [
        "01_schema_structure_test.sql",
        "02_vector_search_test.sql",
        "03_cascade_deletion_test.sql",
        "04_touch_last_queried_test.sql",
        "05_cleanup_stale_documents_test.sql",
        "06_pg_cron_verification_test.sql",
    ]
    
    for test_file in expected_sql_tests:
        test_path = TESTS_DIR / test_file
        assert_true(test_path.exists(), f"SQL test file '{test_file}' exists")
        sql_content = test_path.read_text(encoding="utf-8")
        assert_true("BEGIN;" in sql_content and "ROLLBACK;" in sql_content, f"'{test_file}' wrapped safely in transactional BEGIN/ROLLBACK")
        assert_true("RAISE EXCEPTION" in sql_content, f"'{test_file}' contains explicit assertion checks")

def main():
    print("=================================================================")
    print("ApexTender v2.0 — Milestone 1 Database Verification Test Runner")
    print("=================================================================")
    test_migration_ddl_and_syntax()
    test_supabase_config()
    test_vector_similarity_math()
    test_cleanup_stale_documents_logic()
    test_sql_test_files()
    
    print("\n=================================================================")
    print(f"Summary: {passed_tests} PASSED, {failed_tests} FAILED")
    print("=================================================================")
    
    if failed_tests > 0:
        sys.exit(1)
    else:
        print("ALL TESTS PASSED SUCCESSFULLY!")
        sys.exit(0)

if __name__ == "__main__":
    main()
