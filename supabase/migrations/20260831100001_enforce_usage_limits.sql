-- Enforce hard limits in the usage functions

CREATE OR REPLACE FUNCTION increment_document_count()
RETURNS trigger AS $$
DECLARE
    current_docs int;
BEGIN
    INSERT INTO public.user_usage (user_id, document_count, query_count)
    VALUES (NEW.user_id, 1, 0)
    ON CONFLICT (user_id) DO UPDATE SET 
        document_count = user_usage.document_count + 1,
        updated_at = now()
    RETURNING document_count INTO current_docs;

    IF current_docs > 3 THEN
        RAISE EXCEPTION 'Free tier limit reached: You can only upload up to 3 documents.';
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

CREATE OR REPLACE FUNCTION increment_query_count(p_user_id uuid)
RETURNS void AS $$
DECLARE
    current_queries int;
BEGIN
    INSERT INTO public.user_usage (user_id, document_count, query_count)
    VALUES (p_user_id, 0, 1)
    ON CONFLICT (user_id) DO UPDATE SET 
        query_count = user_usage.query_count + 1,
        updated_at = now()
    RETURNING query_count INTO current_queries;

    IF current_queries > 50 THEN
        RAISE EXCEPTION 'Free tier limit reached: You can only ask up to 50 questions.';
    END IF;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;
