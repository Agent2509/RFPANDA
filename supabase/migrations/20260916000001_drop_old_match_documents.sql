-- Drop the old match_documents function with single filter_document_id
DROP FUNCTION IF EXISTS public.match_documents(vector(1024), float8, integer, uuid, uuid);
