-- ============================================================================
-- Test 03: Foreign Key Cascade Deletion Verification
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user_id uuid := '33333333-3333-3333-3333-333333333333';
    v_doc_id uuid;
    v_chunk_count_before integer;
    v_chunk_count_after integer;
BEGIN
    RAISE NOTICE '>>> Starting Test 03: Cascade Deletion Verification';

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
        INSERT INTO auth.users (id, email) VALUES (v_user_id, 'user_c@example.com') ON CONFLICT (id) DO NOTHING;
    END IF;

    -- 1. Insert parent document
    INSERT INTO public.documents (user_id, name, storage_path, status)
    VALUES (v_user_id, 'CascadeTestDoc.pdf', 'user_c/doc1/CascadeTestDoc.pdf', 'completed')
    RETURNING id INTO v_doc_id;

    -- 2. Insert 5 chunks for the document
    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, token_count)
    VALUES 
        (v_doc_id, v_user_id, 0, 'Chunk 0 content', 20),
        (v_doc_id, v_user_id, 1, 'Chunk 1 content', 25),
        (v_doc_id, v_user_id, 2, 'Chunk 2 content', 30),
        (v_doc_id, v_user_id, 3, 'Chunk 3 content', 35),
        (v_doc_id, v_user_id, 4, 'Chunk 4 content', 40);

    SELECT count(*) INTO v_chunk_count_before FROM public.document_chunks WHERE document_id = v_doc_id;
    IF v_chunk_count_before <> 5 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 5 chunks before delete, got %', v_chunk_count_before;
    END IF;
    RAISE NOTICE '✓ Document and 5 child chunks created.';

    -- 3. Delete parent document
    DELETE FROM public.documents WHERE id = v_doc_id;

    -- 4. Verify chunks were automatically removed by ON DELETE CASCADE
    SELECT count(*) INTO v_chunk_count_after FROM public.document_chunks WHERE document_id = v_doc_id;
    IF v_chunk_count_after <> 0 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 0 chunks after cascade delete, found % orphaned chunks!', v_chunk_count_after;
    END IF;
    RAISE NOTICE '✓ Cascade deletion verified: 0 orphaned chunks remain.';

    RAISE NOTICE '>>> TEST 03 PASSED SUCCESSFULLY: Cascade deletion operational.';
END $$;

ROLLBACK;
