-- Migration for User Usage Limits

CREATE TABLE public.user_usage (
    user_id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
    document_count int DEFAULT 0,
    query_count int DEFAULT 0,
    period_start timestamp with time zone DEFAULT now(),
    updated_at timestamp with time zone DEFAULT now()
);

-- Enable RLS
ALTER TABLE public.user_usage ENABLE ROW LEVEL SECURITY;

-- Allow users to read their own usage
CREATE POLICY "Users can read own usage"
    ON public.user_usage FOR SELECT
    USING (auth.uid() = user_id);

CREATE OR REPLACE FUNCTION increment_document_count()
RETURNS trigger AS $$
BEGIN
    INSERT INTO public.user_usage (user_id, document_count, query_count)
    VALUES (NEW.user_id, 1, 0)
    ON CONFLICT (user_id) DO UPDATE SET 
        document_count = user_usage.document_count + 1,
        updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger to auto-increment doc count when a document is uploaded
CREATE TRIGGER on_document_created
    AFTER INSERT ON public.documents
    FOR EACH ROW EXECUTE FUNCTION increment_document_count();

-- Function for backend to call to increment query count
CREATE OR REPLACE FUNCTION increment_query_count(p_user_id uuid)
RETURNS void AS $$
BEGIN
    INSERT INTO public.user_usage (user_id, document_count, query_count)
    VALUES (p_user_id, 0, 1)
    ON CONFLICT (user_id) DO UPDATE SET 
        query_count = user_usage.query_count + 1,
        updated_at = now();
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

GRANT EXECUTE ON FUNCTION increment_query_count(uuid) TO service_role;
