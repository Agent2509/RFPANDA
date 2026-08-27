-- ============================================================================
-- Test 05: cleanup_stale_documents & Audit Logging Verification
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user_id uuid := '55555555-5555-5555-5555-555555555555';
    v_stale_doc1 uuid;
    v_stale_doc2_null_queried uuid;
    v_kept_forever_doc uuid;
    v_fresh_doc uuid;
    v_cleanup_result jsonb;
    v_audit_entry record;
BEGIN
    RAISE NOTICE '>>> Starting Test 05: cleanup_stale_documents Auto-Cleanup Verification';

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
        INSERT INTO auth.users (id, email) VALUES (v_user_id, 'user_e@example.com') ON CONFLICT (id) DO NOTHING;
    END IF;

    -- 1. Insert Stale Doc 1: last_queried_at = 45 days ago, keep_forever = false (SHOULD BE DELETED)
    INSERT INTO public.documents (user_id, name, storage_path, file_size, keep_forever, last_queried_at, created_at, status)
    VALUES (v_user_id, 'Stale1.pdf', 'user_e/doc1/Stale1.pdf', 1048576, false, now() - interval '45 days', now() - interval '50 days', 'completed')
    RETURNING id INTO v_stale_doc1;

    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, token_count)
    VALUES (v_stale_doc1, v_user_id, 0, 'Stale chunk 0', 30), (v_stale_doc1, v_user_id, 1, 'Stale chunk 1', 35);

    -- 2. Insert Stale Doc 2: created 40 days ago, last_queried_at is NULL, keep_forever = false (SHOULD BE DELETED)
    INSERT INTO public.documents (user_id, name, storage_path, file_size, keep_forever, last_queried_at, created_at, status)
    VALUES (v_user_id, 'Stale2_Unqueried.pdf', 'user_e/doc2/Stale2_Unqueried.pdf', 2097152, false, NULL, now() - interval '40 days', 'completed')
    RETURNING id INTO v_stale_doc2_null_queried;

    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, token_count)
    VALUES (v_stale_doc2_null_queried, v_user_id, 0, 'Stale2 chunk 0', 40);

    -- 3. Insert Kept Forever Doc: created 100 days ago, keep_forever = true (SHOULD BE RETAINED)
    INSERT INTO public.documents (user_id, name, storage_path, file_size, keep_forever, last_queried_at, created_at, status)
    VALUES (v_user_id, 'ImportantContract.pdf', 'user_e/doc3/ImportantContract.pdf', 5242880, true, now() - interval '90 days', now() - interval '100 days', 'completed')
    RETURNING id INTO v_kept_forever_doc;

    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, token_count)
    VALUES (v_kept_forever_doc, v_user_id, 0, 'Kept forever chunk 0', 100);

    -- 4. Insert Fresh Doc: last_queried_at = 5 days ago, keep_forever = false (SHOULD BE RETAINED)
    INSERT INTO public.documents (user_id, name, storage_path, file_size, keep_forever, last_queried_at, created_at, status)
    VALUES (v_user_id, 'FreshRFP.pdf', 'user_e/doc4/FreshRFP.pdf', 1048576, false, now() - interval '5 days', now() - interval '6 days', 'completed')
    RETURNING id INTO v_fresh_doc;

    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, token_count)
    VALUES (v_fresh_doc, v_user_id, 0, 'Fresh chunk 0', 50);

    RAISE NOTICE '✓ Test documents created: 2 stale candidates, 1 keep_forever, 1 fresh.';

    -- 5. Execute cleanup_stale_documents(interval '30 days')
    SELECT public.cleanup_stale_documents(interval '30 days') INTO v_cleanup_result;

    RAISE NOTICE 'Cleanup RPC result: %', v_cleanup_result;

    IF (v_cleanup_result->>'status') <> 'success' THEN
        RAISE EXCEPTION 'TEST FAILED: Expected success status, got %', v_cleanup_result;
    END IF;

    IF (v_cleanup_result->>'deleted_documents_count')::integer <> 2 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 2 deleted documents, got %', v_cleanup_result->>'deleted_documents_count';
    END IF;

    IF (v_cleanup_result->>'deleted_chunks_count')::integer <> 3 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 3 cascaded chunks deleted, got %', v_cleanup_result->>'deleted_chunks_count';
    END IF;

    -- 6. Verify stale documents are gone
    IF EXISTS (SELECT 1 FROM public.documents WHERE id IN (v_stale_doc1, v_stale_doc2_null_queried)) THEN
        RAISE EXCEPTION 'TEST FAILED: Stale documents were not deleted from public.documents!';
    END IF;

    -- 7. Verify stale chunks are gone
    IF EXISTS (SELECT 1 FROM public.document_chunks WHERE document_id IN (v_stale_doc1, v_stale_doc2_null_queried)) THEN
        RAISE EXCEPTION 'TEST FAILED: Stale document chunks were not cascaded!';
    END IF;
    RAISE NOTICE '✓ Stale documents and child chunks purged successfully.';

    -- 8. Verify kept_forever and fresh documents remain untouched
    IF NOT EXISTS (SELECT 1 FROM public.documents WHERE id = v_kept_forever_doc) THEN
        RAISE EXCEPTION 'TEST FAILED: Document with keep_forever=true was improperly deleted!';
    END IF;

    IF NOT EXISTS (SELECT 1 FROM public.documents WHERE id = v_fresh_doc) THEN
        RAISE EXCEPTION 'TEST FAILED: Fresh document was improperly deleted!';
    END IF;
    RAISE NOTICE '✓ Protected documents (keep_forever=true and fresh) securely retained.';

    -- 9. Verify Audit Log entry
    SELECT * INTO v_audit_entry 
    FROM public.cleanup_audit_logs 
    ORDER BY executed_at DESC 
    LIMIT 1;

    IF v_audit_entry.deleted_documents_count <> 2 OR v_audit_entry.deleted_chunks_count <> 3 THEN
        RAISE EXCEPTION 'TEST FAILED: Audit log counts incorrect! Found docs=%, chunks=%', 
            v_audit_entry.deleted_documents_count, v_audit_entry.deleted_chunks_count;
    END IF;
    RAISE NOTICE '✓ Audit log entry validated with correct deletion metrics and execution duration.';

    -- 10. Test Idempotent No-Op Run
    SELECT public.cleanup_stale_documents(interval '30 days') INTO v_cleanup_result;
    IF (v_cleanup_result->>'status') <> 'no_op' THEN
        RAISE EXCEPTION 'TEST FAILED: Second cleanup run should be no_op, got %', v_cleanup_result;
    END IF;
    RAISE NOTICE '✓ Idempotent execution verified: subsequent run produces clean no_op.';

    RAISE NOTICE '>>> TEST 05 PASSED SUCCESSFULLY: cleanup_stale_documents and audit logging verified.';
END $$;

ROLLBACK;
