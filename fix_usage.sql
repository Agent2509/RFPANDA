CREATE OR REPLACE FUNCTION decrement_document_count()
RETURNS trigger AS $$
BEGIN
    UPDATE public.user_usage
    SET document_count = GREATEST(document_count - 1, 0), updated_at = now()
    WHERE user_id = OLD.user_id;
    RETURN OLD;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

DROP TRIGGER IF EXISTS on_document_deleted ON public.documents;
CREATE TRIGGER on_document_deleted
    AFTER DELETE ON public.documents
    FOR EACH ROW EXECUTE FUNCTION decrement_document_count();

-- Recalculate current usage limits based on actual rows
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
