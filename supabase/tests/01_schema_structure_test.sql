-- ============================================================================
-- Test 01: Database Schema, Tables, Columns, Constraints & Indexes Verification
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_missing_tables text[] := ARRAY[]::text[];
    v_missing_cols text[] := ARRAY[]::text[];
    v_missing_indexes text[] := ARRAY[]::text[];
    v_rls_enabled boolean;
BEGIN
    RAISE NOTICE '>>> Starting Test 01: Schema Structure Verification';

    -- 1. Verify Tables Exist
    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'documents') THEN
        v_missing_tables := array_append(v_missing_tables, 'public.documents');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'document_chunks') THEN
        v_missing_tables := array_append(v_missing_tables, 'public.document_chunks');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'public' AND table_name = 'cleanup_audit_logs') THEN
        v_missing_tables := array_append(v_missing_tables, 'public.cleanup_audit_logs');
    END IF;

    IF array_length(v_missing_tables, 1) > 0 THEN
        RAISE EXCEPTION 'TEST FAILED: Missing required tables: %', v_missing_tables;
    END IF;
    RAISE NOTICE '✓ All required tables exist (documents, document_chunks, cleanup_audit_logs).';

    -- 2. Verify Key Columns in public.documents
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'id') THEN
        v_missing_cols := array_append(v_missing_cols, 'documents.id');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'user_id') THEN
        v_missing_cols := array_append(v_missing_cols, 'documents.user_id');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'storage_path') THEN
        v_missing_cols := array_append(v_missing_cols, 'documents.storage_path');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'keep_forever') THEN
        v_missing_cols := array_append(v_missing_cols, 'documents.keep_forever');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'documents' AND column_name = 'last_queried_at') THEN
        v_missing_cols := array_append(v_missing_cols, 'documents.last_queried_at');
    END IF;

    -- 3. Verify Key Columns in public.document_chunks
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'document_chunks' AND column_name = 'document_id') THEN
        v_missing_cols := array_append(v_missing_cols, 'document_chunks.document_id');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'document_chunks' AND column_name = 'embedding') THEN
        v_missing_cols := array_append(v_missing_cols, 'document_chunks.embedding');
    END IF;

    -- 4. Verify Key Columns in public.cleanup_audit_logs
    IF NOT EXISTS (SELECT 1 FROM information_schema.columns WHERE table_schema = 'public' AND table_name = 'cleanup_audit_logs' AND column_name = 'executed_at') THEN
        v_missing_cols := array_append(v_missing_cols, 'cleanup_audit_logs.executed_at');
    END IF;

    IF array_length(v_missing_cols, 1) > 0 THEN
        RAISE EXCEPTION 'TEST FAILED: Missing required columns: %', v_missing_cols;
    END IF;
    RAISE NOTICE '✓ All required columns verified across tables.';

    -- 5. Verify Indexes Exist
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'document_chunks' AND indexname = 'idx_document_chunks_embedding_hnsw') THEN
        v_missing_indexes := array_append(v_missing_indexes, 'idx_document_chunks_embedding_hnsw');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'documents' AND indexname = 'idx_documents_user_id') THEN
        v_missing_indexes := array_append(v_missing_indexes, 'idx_documents_user_id');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'documents' AND indexname = 'idx_documents_last_queried_at') THEN
        v_missing_indexes := array_append(v_missing_indexes, 'idx_documents_last_queried_at');
    END IF;
    IF NOT EXISTS (SELECT 1 FROM pg_indexes WHERE schemaname = 'public' AND tablename = 'document_chunks' AND indexname = 'idx_document_chunks_document_id') THEN
        v_missing_indexes := array_append(v_missing_indexes, 'idx_document_chunks_document_id');
    END IF;

    IF array_length(v_missing_indexes, 1) > 0 THEN
        RAISE EXCEPTION 'TEST FAILED: Missing required indexes: %', v_missing_indexes;
    END IF;
    RAISE NOTICE '✓ HNSW vector index and B-Tree indexes verified.';

    -- 6. Verify Row Level Security (RLS) is enabled
    SELECT rowsecurity INTO v_rls_enabled FROM pg_tables WHERE schemaname = 'public' AND tablename = 'documents';
    IF NOT v_rls_enabled THEN
        RAISE EXCEPTION 'TEST FAILED: RLS not enabled on public.documents';
    END IF;

    SELECT rowsecurity INTO v_rls_enabled FROM pg_tables WHERE schemaname = 'public' AND tablename = 'document_chunks';
    IF NOT v_rls_enabled THEN
        RAISE EXCEPTION 'TEST FAILED: RLS not enabled on public.document_chunks';
    END IF;

    SELECT rowsecurity INTO v_rls_enabled FROM pg_tables WHERE schemaname = 'public' AND tablename = 'cleanup_audit_logs';
    IF NOT v_rls_enabled THEN
        RAISE EXCEPTION 'TEST FAILED: RLS not enabled on public.cleanup_audit_logs';
    END IF;
    RAISE NOTICE '✓ RLS enabled on all tables.';

    RAISE NOTICE '>>> TEST 01 PASSED SUCCESSFULLY: Schema structure is 100%% compliant.';
END $$;

ROLLBACK;
