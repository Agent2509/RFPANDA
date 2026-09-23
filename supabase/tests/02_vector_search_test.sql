-- ============================================================================
-- Test 02: Vector Insertion, Cosine Distance & match_documents Verification
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user_a uuid := '11111111-1111-1111-1111-111111111111';
    v_user_b uuid := '22222222-2222-2222-2222-222222222222';
    v_doc_a1 uuid;
    v_doc_a2 uuid;
    v_doc_ids uuid[];
    v_doc_b1 uuid;
    
    -- Construct 1024-dim test vectors
    v_vec_target vector(1024);
    v_vec_near vector(1024);
    v_vec_far vector(1024);
    v_zero_pad text := repeat(',0', 1022);
    
    v_match_count integer;
    v_top_sim float8;
    v_top_doc_id uuid;
    v_cross_tenant_count integer;
BEGIN
    RAISE NOTICE '>>> Starting Test 02: Vector Search & Multi-Tenant Isolation';

    -- 1. Create auth users if auth.users table exists
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
        INSERT INTO auth.users (id, email) VALUES (v_user_a, 'user_a@example.com') ON CONFLICT (id) DO NOTHING;
        INSERT INTO auth.users (id, email) VALUES (v_user_b, 'user_b@example.com') ON CONFLICT (id) DO NOTHING;
    END IF;

    -- 2. Build test vectors
    -- Vector Target: [1.0, 0.0, 0, 0, ...]
    -- Vector Near:   [0.9, 0.1, 0, 0, ...]
    -- Vector Far:    [0.0, 1.0, 0, 0, ...]
    EXECUTE format('SELECT ''[1.0,0.0%s]''::vector(1024)', v_zero_pad) INTO v_vec_target;
    EXECUTE format('SELECT ''[0.9,0.1%s]''::vector(1024)', v_zero_pad) INTO v_vec_near;
    EXECUTE format('SELECT ''[0.0,1.0%s]''::vector(1024)', v_zero_pad) INTO v_vec_far;

    -- 3. Insert Documents for User A
    INSERT INTO public.documents (user_id, name, storage_path, status)
    VALUES (v_user_a, 'UserA_Doc1.pdf', 'user_a/doc1/UserA_Doc1.pdf', 'completed')
    RETURNING id INTO v_doc_a1;

    INSERT INTO public.documents (user_id, name, storage_path, status)
    VALUES (v_user_a, 'UserA_Doc2.pdf', 'user_a/doc2/UserA_Doc2.pdf', 'completed')
    RETURNING id INTO v_doc_a2;

    v_doc_ids := ARRAY[v_doc_a2];

    -- 4. Insert Document for User B
    INSERT INTO public.documents (user_id, name, storage_path, status)
    VALUES (v_user_b, 'UserB_Doc1.pdf', 'user_b/doc1/UserB_Doc1.pdf', 'completed')
    RETURNING id INTO v_doc_b1;

    -- 5. Insert Chunks for User A Doc 1 (Near target)
    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, embedding, token_count)
    VALUES (v_doc_a1, v_user_a, 0, 'Section 1: Target Match Content for Doc A1', v_vec_target, 45);

    -- 6. Insert Chunks for User A Doc 2 (Near vector)
    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, embedding, token_count)
    VALUES (v_doc_a2, v_user_a, 0, 'Section 1: Moderate Match Content for Doc A2', v_vec_near, 48);

    -- 7. Insert Chunks for User B Doc 1 (Identical target vector, but belongs to User B)
    INSERT INTO public.document_chunks (document_id, user_id, chunk_index, content, embedding, token_count)
    VALUES (v_doc_b1, v_user_b, 0, 'User B Secret Content with Target Vector', v_vec_target, 50);

    RAISE NOTICE '✓ Documents and 1024-dimensional chunks inserted successfully.';

    -- 8. Test match_documents for User A
    SELECT count(*), max(similarity), (array_agg(document_id ORDER BY similarity DESC))[1]
    INTO v_match_count, v_top_sim, v_top_doc_id
    FROM public.match_documents(
        query_embedding => v_vec_target,
        match_threshold => 0.5,
        match_count => 10,
        filter_user_id => v_user_a
    );

    IF v_match_count <> 2 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 2 matches for User A, got %', v_match_count;
    END IF;

    IF v_top_doc_id <> v_doc_a1 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected top match to be doc_a1 (%), got %', v_doc_a1, v_top_doc_id;
    END IF;

    IF v_top_sim < 0.99 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected exact match similarity ~1.0, got %', v_top_sim;
    END IF;
    RAISE NOTICE '✓ match_documents similarity search and ordering verified (top similarity: %).', v_top_sim;

    -- 9. Test Scoped Document Filter (filter_document_ids)
    SELECT count(*)
    INTO v_match_count
    FROM public.match_documents(
        query_embedding => v_vec_target,
        match_threshold => 0.1,
        match_count => 10,
        filter_user_id => v_user_a,
        filter_document_ids => v_doc_ids
    );

    IF v_match_count <> 1 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 1 match when filtering by doc_a2, got %', v_match_count;
    END IF;
    RAISE NOTICE '✓ filter_document_ids single-document scoping verified.';

    -- 10. Test Multi-Tenant Isolation (User A MUST NOT see User B data)
    SELECT count(*)
    INTO v_cross_tenant_count
    FROM public.match_documents(
        query_embedding => v_vec_target,
        match_threshold => 0.0,
        match_count => 100,
        filter_user_id => v_user_a
    )
    WHERE document_id = v_doc_b1;

    IF v_cross_tenant_count > 0 THEN
        RAISE EXCEPTION 'CRITICAL SECURITY VIOLATION: User A query returned User B document!';
    END IF;
    RAISE NOTICE '✓ Multi-tenant isolation verified: Zero cross-tenant leakage.';

    RAISE NOTICE '>>> TEST 02 PASSED SUCCESSFULLY: Vector search and tenant isolation confirmed.';
END $$;

ROLLBACK;
