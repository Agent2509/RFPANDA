-- ============================================================================
-- RFPanda v2.0 — Security Fix Migration
-- Migration: 20260831000000_security_fixes.sql
-- Fixes: IDOR in match_documents, unrestricted cleanup, touch ownership
-- ============================================================================

-- 1. Fix match_documents: Force auth.uid() for authenticated callers
--    Only service_role can override filter_user_id
CREATE OR REPLACE FUNCTION public.match_documents(
    query_embedding vector(1024),
    match_threshold float8 DEFAULT 0.2,
    match_count integer DEFAULT 5,
    filter_user_id uuid DEFAULT NULL,
    filter_document_ids uuid[] DEFAULT NULL
)
RETURNS TABLE (
    id uuid,
    chunk_id uuid,
    document_id uuid,
    document_name text,
    chunk_index integer,
    content text,
    similarity float8,
    metadata jsonb,
    token_count integer
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    v_target_user_id uuid;
    v_calling_role text := current_setting('request.jwt.claim.role', true);
BEGIN
    -- Security: Force auth.uid() for authenticated callers
    -- Only service_role/postgres can override filter_user_id
    IF v_calling_role = 'authenticated' AND auth.uid() IS NOT NULL THEN
        v_target_user_id := auth.uid();
    ELSE
        v_target_user_id := COALESCE(filter_user_id, auth.uid());
    END IF;

    IF v_target_user_id IS NULL THEN
        RAISE EXCEPTION 'Access denied: No authenticated user or filter_user_id provided.';
    END IF;

    -- Set HNSW search candidate list size for optimal recall
    SET LOCAL hnsw.ef_search = 40;

    RETURN QUERY
    SELECT
        dc.id AS id,
        dc.id AS chunk_id,
        dc.document_id,
        d.name AS document_name,
        dc.chunk_index,
        dc.content,
        (1 - (dc.embedding <=> query_embedding)) AS similarity,
        dc.metadata,
        dc.token_count
    FROM public.document_chunks dc
    INNER JOIN public.documents d ON d.id = dc.document_id
    WHERE dc.user_id = v_target_user_id
      AND (filter_document_ids IS NULL OR dc.document_id = ANY(filter_document_ids))
      AND (1 - (dc.embedding <=> query_embedding)) >= match_threshold
    ORDER BY dc.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- 2. Fix touch_document_last_queried: Add ownership check
CREATE OR REPLACE FUNCTION public.touch_document_last_queried(
    p_document_ids uuid[]
)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, extensions
AS $$
DECLARE
    v_updated_count integer := 0;
    v_calling_role text := current_setting('request.jwt.claim.role', true);
BEGIN
    IF p_document_ids IS NULL OR array_length(p_document_ids, 1) IS NULL THEN
        RETURN 0;
    END IF;

    UPDATE public.documents
    SET
        last_queried_at = now(),
        updated_at = now()
    WHERE id = ANY(p_document_ids)
      AND (v_calling_role = 'service_role' OR user_id = auth.uid());

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RETURN v_updated_count;
END;
$$;

-- 3. Lock down cleanup_stale_documents: Only service_role and postgres
REVOKE EXECUTE ON FUNCTION public.cleanup_stale_documents(interval) FROM PUBLIC, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.cleanup_stale_documents(interval) TO service_role, postgres;

-- 4. Add missing index on cleanup_audit_logs
CREATE INDEX IF NOT EXISTS idx_cleanup_audit_logs_executed_at
ON public.cleanup_audit_logs(executed_at DESC);
