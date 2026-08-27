-- ============================================================================
-- Test 04: touch_document_last_queried Stored Procedure Verification
-- ============================================================================

\set ON_ERROR_STOP on

BEGIN;

DO $$
DECLARE
    v_user_id uuid := '44444444-4444-4444-4444-444444444444';
    v_doc1_id uuid;
    v_doc2_id uuid;
    v_old_timestamp timestamptz := now() - interval '10 days';
    v_updated_count integer;
    v_new_last_queried timestamptz;
BEGIN
    RAISE NOTICE '>>> Starting Test 04: touch_document_last_queried Verification';

    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'auth' AND table_name = 'users') THEN
        INSERT INTO auth.users (id, email) VALUES (v_user_id, 'user_d@example.com') ON CONFLICT (id) DO NOTHING;
    END IF;

    -- 1. Insert documents with old last_queried_at
    INSERT INTO public.documents (user_id, name, storage_path, last_queried_at, status)
    VALUES (v_user_id, 'Doc1_Touch.pdf', 'user_d/doc1/Doc1_Touch.pdf', v_old_timestamp, 'completed')
    RETURNING id INTO v_doc1_id;

    INSERT INTO public.documents (user_id, name, storage_path, last_queried_at, status)
    VALUES (v_user_id, 'Doc2_Touch.pdf', 'user_d/doc2/Doc2_Touch.pdf', v_old_timestamp, 'completed')
    RETURNING id INTO v_doc2_id;

    -- 2. Execute touch_document_last_queried for doc1
    SELECT public.touch_document_last_queried(ARRAY[v_doc1_id]) INTO v_updated_count;

    IF v_updated_count <> 1 THEN
        RAISE EXCEPTION 'TEST FAILED: Expected 1 updated document, got %', v_updated_count;
    END IF;

    -- 3. Verify doc1 timestamp is now updated (> now() - interval '1 minute')
    SELECT last_queried_at INTO v_new_last_queried FROM public.documents WHERE id = v_doc1_id;
    IF v_new_last_queried < (now() - interval '1 minute') THEN
        RAISE EXCEPTION 'TEST FAILED: Document 1 last_queried_at was not updated to current time! Got %', v_new_last_queried;
    END IF;
    RAISE NOTICE '✓ Document 1 timestamp touched successfully (updated from % to %).', v_old_timestamp, v_new_last_queried;

    -- 4. Verify doc2 was untouched
    SELECT last_queried_at INTO v_new_last_queried FROM public.documents WHERE id = v_doc2_id;
    IF v_new_last_queried > (now() - interval '1 day') THEN
        RAISE EXCEPTION 'TEST FAILED: Document 2 was unexpectedly modified!';
    END IF;
    RAISE NOTICE '✓ Unspecified documents remained untouched.';

    -- 5. Test batch touch
    SELECT public.touch_document_last_queried(ARRAY[v_doc1_id, v_doc2_id]) INTO v_updated_count;
    IF v_updated_count <> 2 THEN
        RAISE EXCEPTION 'TEST FAILED: Batch touch expected 2, got %', v_updated_count;
    END IF;
    RAISE NOTICE '✓ Batch touch updated both documents.';

    RAISE NOTICE '>>> TEST 04 PASSED SUCCESSFULLY: touch_document_last_queried verified.';
END $$;

ROLLBACK;
