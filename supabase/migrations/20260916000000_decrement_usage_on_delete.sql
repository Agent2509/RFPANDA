-- ============================================================================
-- RFPanda v2.1 — Usage Quota Fix
-- Migration: 20260916000000_decrement_usage_on_delete.sql
-- Decrements usage quota when a document is deleted and recalculates existing limits
-- ============================================================================

-- 1. Create the function to refund quota on delete
CREATE OR REPLACE FUNCTION decrement_document_count()
RETURNS trigger AS $$
BEGIN
    UPDATE public.user_usage
    SET document_count = GREATEST(document_count - 1, 0), updated_at = now()
    WHERE user_id = OLD.user_id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- 2. Attach the trigger to the documents table
DROP TRIGGER IF EXISTS on_document_deleted ON public.documents;
CREATE TRIGGER on_document_deleted
    AFTER DELETE ON public.documents
    FOR EACH ROW EXECUTE FUNCTION decrement_document_count();

-- 3. Reset everyone's usage limits based on their actual current documents
WITH actual_counts AS (
    SELECT user_id, count(*) as actual_count
    FROM public.documents
    GROUP BY user_id
)
UPDATE public.user_usage u
SET document_count = COALESCE(a.actual_count, 0)
FROM (SELECT DISTINCT user_id FROM public.user_usage) users
LEFT JOIN actual_counts a ON users.user_id = a.user_id
WHERE u.user_id = users.user_id;
