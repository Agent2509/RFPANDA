-- ============================================================================
-- RFPanda v2.1 — Fix Usage Limit Race Condition
-- Migration: 20260915000000_fix_usage_limit_race.sql
-- Uses pg_advisory_xact_lock to serialize concurrent limit checks per user.
-- ============================================================================

-- 1. Fix increment_document_count: check BEFORE increment, use advisory lock
CREATE OR REPLACE FUNCTION increment_document_count()
RETURNS trigger AS $$
DECLARE
    current_docs int;
BEGIN
    -- Serialize per-user to prevent TOCTOU race under concurrent uploads
    PERFORM pg_advisory_xact_lock(hashtext('doc_limit_' || NEW.user_id::text));

    SELECT document_count INTO current_docs
    FROM public.user_usage
    WHERE user_id = NEW.user_id
    FOR UPDATE;

    IF current_docs IS NULL THEN
        -- First document for this user — insert usage row
        INSERT INTO public.user_usage (user_id, document_count, query_count)
        VALUES (NEW.user_id, 1, 0);
    ELSE
        -- Check limit BEFORE incrementing
        IF current_docs >= 3 THEN
            RAISE EXCEPTION 'Free tier limit reached: You can only upload up to 3 documents.';
        END IF;
        UPDATE public.user_usage
        SET document_count = document_count + 1, updated_at = now()
        WHERE user_id = NEW.user_id;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Fix increment_query_count: check BEFORE increment, use advisory lock
CREATE OR REPLACE FUNCTION increment_query_count(p_user_id uuid)
RETURNS void AS $$
DECLARE
    current_queries int;
BEGIN
    -- Serialize per-user to prevent TOCTOU race under concurrent queries
    PERFORM pg_advisory_xact_lock(hashtext('query_limit_' || p_user_id::text));

    SELECT query_count INTO current_queries
    FROM public.user_usage
    WHERE user_id = p_user_id
    FOR UPDATE;

    IF current_queries IS NULL THEN
        -- First query for this user — insert usage row
        INSERT INTO public.user_usage (user_id, document_count, query_count)
        VALUES (p_user_id, 0, 1);
    ELSE
        -- Check limit BEFORE incrementing
        IF current_queries >= 50 THEN
            RAISE EXCEPTION 'Free tier limit reached: You can only ask up to 50 questions.';
        END IF;
        UPDATE public.user_usage
        SET query_count = query_count + 1, updated_at = now()
        WHERE user_id = p_user_id;
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
