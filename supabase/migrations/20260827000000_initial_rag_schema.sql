-- ============================================================================
-- ApexTender v2.0 — Database Schema, pgvector, RLS & pg_cron Auto-Cleanup
-- Migration: 20260827000000_initial_rag_schema.sql
-- ============================================================================

-- Ensure schemas exist
CREATE SCHEMA IF NOT EXISTS "extensions";
CREATE SCHEMA IF NOT EXISTS "public";
CREATE SCHEMA IF NOT EXISTS "auth";
CREATE SCHEMA IF NOT EXISTS "storage";

-- 1. POSTGRESQL EXTENSIONS
CREATE EXTENSION IF NOT EXISTS "vector" WITH SCHEMA "extensions";
CREATE EXTENSION IF NOT EXISTS "pg_cron" WITH SCHEMA "extensions";
CREATE EXTENSION IF NOT EXISTS "pgcrypto" WITH SCHEMA "extensions";
CREATE EXTENSION IF NOT EXISTS "pg_net" WITH SCHEMA "extensions";

-- Set search_path for current transaction
SET search_path = public, extensions, auth, storage;

-- 2. TABLES

-- 2.1 Documents Table
CREATE TABLE IF NOT EXISTS public.documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    name TEXT NOT NULL,
    storage_path TEXT NOT NULL UNIQUE,
    file_size BIGINT NOT NULL DEFAULT 0,
    mime_type TEXT NOT NULL DEFAULT 'application/pdf',
    status TEXT NOT NULL DEFAULT 'uploaded' CHECK (status IN ('uploaded', 'processing', 'completed', 'processed', 'failed', 'fallback_processing', 'awaiting_fallback_parse')),
    error_message TEXT NULL,
    keep_forever BOOLEAN NOT NULL DEFAULT false,
    last_queried_at TIMESTAMPTZ DEFAULT now(),
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 2.2 Document Chunks Table (1024 dimensions for Voyage AI voyage-3 / voyage-3-lite)
CREATE TABLE IF NOT EXISTS public.document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES public.documents(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES auth.users(id) ON DELETE CASCADE,
    chunk_index INTEGER NOT NULL,
    content TEXT NOT NULL,
    embedding vector(1024),
    token_count INTEGER DEFAULT 0,
    metadata JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_document_chunk UNIQUE (document_id, chunk_index)
);

-- 2.3 Cleanup Audit Logs Table
CREATE TABLE IF NOT EXISTS public.cleanup_audit_logs (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    executed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    documents_deleted_count INTEGER NOT NULL DEFAULT 0,
    chunks_deleted_count INTEGER NOT NULL DEFAULT 0,
    deleted_documents_count INTEGER NOT NULL DEFAULT 0,
    deleted_chunks_count INTEGER NOT NULL DEFAULT 0,
    freed_bytes_estimate BIGINT NOT NULL DEFAULT 0,
    execution_duration_ms INTEGER NOT NULL DEFAULT 0,
    details JSONB NOT NULL DEFAULT '{}'::jsonb
);

-- 3. TRIGGERS

-- Auto-update updated_at on documents
CREATE OR REPLACE FUNCTION public.handle_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = now();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS tr_documents_updated_at ON public.documents;
CREATE TRIGGER tr_documents_updated_at
BEFORE UPDATE ON public.documents
FOR EACH ROW
EXECUTE FUNCTION public.handle_updated_at();

-- 4. INDEXES

-- 4.1 Vector HNSW Cosine Index (m=16, ef_construction=64)
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding_hnsw 
ON public.document_chunks 
USING hnsw (embedding vector_cosine_ops)
WITH (m = 16, ef_construction = 64);

-- 4.2 Documents B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_documents_user_id ON public.documents(user_id);
CREATE INDEX IF NOT EXISTS idx_documents_last_queried_at ON public.documents(last_queried_at);
CREATE INDEX IF NOT EXISTS idx_documents_keep_forever ON public.documents(keep_forever);
CREATE INDEX IF NOT EXISTS idx_documents_status ON public.documents(status);
CREATE INDEX IF NOT EXISTS idx_documents_cleanup_scan ON public.documents(keep_forever, last_queried_at, created_at);

-- 4.3 Document Chunks B-Tree Indexes
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON public.document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_user_id ON public.document_chunks(user_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_composite ON public.document_chunks(user_id, document_id, chunk_index);

-- 5. ROW LEVEL SECURITY (RLS)

ALTER TABLE public.documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.document_chunks ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.cleanup_audit_logs ENABLE ROW LEVEL SECURITY;

-- 5.1 Documents Policies
DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can view own documents" ON public.documents;
    DROP POLICY IF EXISTS "Users can insert own documents" ON public.documents;
    DROP POLICY IF EXISTS "Users can update own documents" ON public.documents;
    DROP POLICY IF EXISTS "Users can delete own documents" ON public.documents;
    DROP POLICY IF EXISTS "Service role has full access to documents" ON public.documents;
END $$;

CREATE POLICY "Users can view own documents" 
ON public.documents FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own documents" 
ON public.documents FOR INSERT 
TO authenticated 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own documents" 
ON public.documents FOR UPDATE 
TO authenticated 
USING (auth.uid() = user_id) 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own documents" 
ON public.documents FOR DELETE 
TO authenticated 
USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to documents" 
ON public.documents FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- 5.2 Document Chunks Policies
DO $$ BEGIN
    DROP POLICY IF EXISTS "Users can view own document chunks" ON public.document_chunks;
    DROP POLICY IF EXISTS "Users can insert own document chunks" ON public.document_chunks;
    DROP POLICY IF EXISTS "Users can update own document chunks" ON public.document_chunks;
    DROP POLICY IF EXISTS "Users can delete own document chunks" ON public.document_chunks;
    DROP POLICY IF EXISTS "Service role has full access to document chunks" ON public.document_chunks;
END $$;

CREATE POLICY "Users can view own document chunks" 
ON public.document_chunks FOR SELECT 
TO authenticated 
USING (auth.uid() = user_id);

CREATE POLICY "Users can insert own document chunks" 
ON public.document_chunks FOR INSERT 
TO authenticated 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can update own document chunks" 
ON public.document_chunks FOR UPDATE 
TO authenticated 
USING (auth.uid() = user_id) 
WITH CHECK (auth.uid() = user_id);

CREATE POLICY "Users can delete own document chunks" 
ON public.document_chunks FOR DELETE 
TO authenticated 
USING (auth.uid() = user_id);

CREATE POLICY "Service role has full access to document chunks" 
ON public.document_chunks FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- 5.3 Cleanup Audit Logs Policies
DO $$ BEGIN
    DROP POLICY IF EXISTS "Service role can manage cleanup logs" ON public.cleanup_audit_logs;
END $$;

CREATE POLICY "Service role can manage cleanup logs" 
ON public.cleanup_audit_logs FOR ALL 
TO service_role 
USING (true) 
WITH CHECK (true);

-- 6. STORAGE BUCKET CONFIGURATION & POLICIES
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'buckets') THEN
        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'rfp-documents', 
            'rfp-documents', 
            false, 
            52428800, -- 50MB file size limit
            ARRAY['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']
        )
        ON CONFLICT (id) DO UPDATE SET
            public = false,
            file_size_limit = 52428800,
            allowed_mime_types = ARRAY['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'];

        INSERT INTO storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
        VALUES (
            'documents', 
            'documents', 
            false, 
            52428800,
            ARRAY['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword']
        )
        ON CONFLICT (id) DO UPDATE SET
            public = false,
            file_size_limit = 52428800,
            allowed_mime_types = ARRAY['application/pdf', 'text/plain', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/msword'];
    END IF;
END $$;

DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema = 'storage' AND table_name = 'objects') THEN
        DROP POLICY IF EXISTS "Allow authenticated users to upload their own files" ON storage.objects;
        DROP POLICY IF EXISTS "Allow authenticated users to read their own files" ON storage.objects;
        DROP POLICY IF EXISTS "Allow authenticated users to update their own files" ON storage.objects;
        DROP POLICY IF EXISTS "Allow authenticated users to delete their own files" ON storage.objects;

        CREATE POLICY "Allow authenticated users to upload their own files"
        ON storage.objects FOR INSERT TO authenticated
        WITH CHECK (
            (bucket_id = 'rfp-documents' OR bucket_id = 'documents')
            AND (storage.foldername(name))[1] = auth.uid()::text
        );

        CREATE POLICY "Allow authenticated users to read their own files"
        ON storage.objects FOR SELECT TO authenticated
        USING (
            (bucket_id = 'rfp-documents' OR bucket_id = 'documents')
            AND (storage.foldername(name))[1] = auth.uid()::text
        );

        CREATE POLICY "Allow authenticated users to update their own files"
        ON storage.objects FOR UPDATE TO authenticated
        USING (
            (bucket_id = 'rfp-documents' OR bucket_id = 'documents')
            AND (storage.foldername(name))[1] = auth.uid()::text
        );

        CREATE POLICY "Allow authenticated users to delete their own files"
        ON storage.objects FOR DELETE TO authenticated
        USING (
            (bucket_id = 'rfp-documents' OR bucket_id = 'documents')
            AND (storage.foldername(name))[1] = auth.uid()::text
        );
    END IF;
END $$;

-- 7. STORED PROCEDURES / RPC FUNCTIONS

-- 7.1 match_documents
-- Performs cosine similarity search using pgvector (<=> operator)
CREATE OR REPLACE FUNCTION public.match_documents(
    query_embedding vector(1024),
    match_threshold float8 DEFAULT 0.2,
    match_count integer DEFAULT 5,
    filter_user_id uuid DEFAULT NULL,
    filter_document_id uuid DEFAULT NULL
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
BEGIN
    -- Determine target user: prefer explicit filter_user_id, fallback to auth.uid()
    v_target_user_id := COALESCE(filter_user_id, auth.uid());
    
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
      AND (filter_document_id IS NULL OR dc.document_id = filter_document_id)
      AND (1 - (dc.embedding <=> query_embedding)) >= match_threshold
    ORDER BY dc.embedding <=> query_embedding ASC
    LIMIT match_count;
END;
$$;

-- 7.2 touch_document_last_queried
-- Updates last_queried_at and updated_at for queried documents
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
BEGIN
    IF p_document_ids IS NULL OR array_length(p_document_ids, 1) IS NULL THEN
        RETURN 0;
    END IF;

    UPDATE public.documents
    SET 
        last_queried_at = now(),
        updated_at = now()
    WHERE id = ANY(p_document_ids);

    GET DIAGNOSTICS v_updated_count = ROW_COUNT;
    RETURN v_updated_count;
END;
$$;

-- 7.3 cleanup_stale_documents
-- Deletes unqueried documents where keep_forever = false older than retention_interval
CREATE OR REPLACE FUNCTION public.cleanup_stale_documents(
    retention_interval interval DEFAULT interval '30 days'
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, storage, extensions
AS $$
DECLARE
    v_start_time timestamptz := clock_timestamp();
    v_cutoff_time timestamptz;
    v_doc_ids uuid[];
    v_storage_paths text[];
    v_deleted_docs_count integer := 0;
    v_deleted_chunks_count integer := 0;
    v_freed_bytes bigint := 0;
    v_duration_ms integer := 0;
    v_result jsonb;
BEGIN
    v_cutoff_time := now() - retention_interval;

    -- 1. Identify candidate documents for pruning
    SELECT 
        COALESCE(array_agg(id), ARRAY[]::uuid[]),
        COALESCE(array_agg(storage_path), ARRAY[]::text[]),
        COALESCE(SUM(file_size), 0)
    INTO 
        v_doc_ids,
        v_storage_paths,
        v_freed_bytes
    FROM public.documents
    WHERE keep_forever = false
      AND COALESCE(last_queried_at, created_at) < v_cutoff_time;

    -- Check if any stale documents were found
    IF array_length(v_doc_ids, 1) IS NULL OR array_length(v_doc_ids, 1) = 0 THEN
        v_duration_ms := EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_start_time))::integer;
        RETURN jsonb_build_object(
            'status', 'no_op',
            'message', 'No stale documents found exceeding retention window.',
            'cutoff_time', v_cutoff_time,
            'deleted_documents_count', 0,
            'documents_deleted_count', 0,
            'deleted_chunks_count', 0,
            'chunks_deleted_count', 0,
            'freed_bytes', 0,
            'execution_duration_ms', v_duration_ms
        );
    END IF;

    -- 2. Count chunks that will be cascaded
    SELECT COUNT(*)
    INTO v_deleted_chunks_count
    FROM public.document_chunks
    WHERE document_id = ANY(v_doc_ids);

    -- 3. Delete underlying storage objects from storage.objects
    BEGIN
        DELETE FROM storage.objects
        WHERE (bucket_id = 'rfp-documents' OR bucket_id = 'documents')
          AND name = ANY(v_storage_paths);
    EXCEPTION WHEN OTHERS THEN
        -- Gracefully handle case where storage table is missing
    END;

    -- 4. Delete documents (cascades to document_chunks via FK ON DELETE CASCADE)
    DELETE FROM public.documents
    WHERE id = ANY(v_doc_ids);

    GET DIAGNOSTICS v_deleted_docs_count = ROW_COUNT;

    v_duration_ms := EXTRACT(MILLISECONDS FROM (clock_timestamp() - v_start_time))::integer;

    -- 5. Record entry in cleanup_audit_logs
    INSERT INTO public.cleanup_audit_logs (
        executed_at,
        documents_deleted_count,
        chunks_deleted_count,
        deleted_documents_count,
        deleted_chunks_count,
        freed_bytes_estimate,
        execution_duration_ms,
        details
    ) VALUES (
        now(),
        v_deleted_docs_count,
        v_deleted_chunks_count,
        v_deleted_docs_count,
        v_deleted_chunks_count,
        v_freed_bytes,
        v_duration_ms,
        jsonb_build_object(
            'retention_interval', retention_interval::text,
            'cutoff_time', v_cutoff_time,
            'deleted_doc_ids', v_doc_ids,
            'deleted_storage_paths', v_storage_paths
        )
    );

    v_result := jsonb_build_object(
        'status', 'success',
        'deleted_documents_count', v_deleted_docs_count,
        'documents_deleted_count', v_deleted_docs_count,
        'deleted_chunks_count', v_deleted_chunks_count,
        'chunks_deleted_count', v_deleted_chunks_count,
        'freed_bytes', v_freed_bytes,
        'freed_bytes_estimate', v_freed_bytes,
        'cutoff_time', v_cutoff_time,
        'execution_duration_ms', v_duration_ms,
        'executed_at', now()
    );

    RETURN v_result;
END;
$$;

-- 8. PG_CRON SCHEDULE
DO $$
BEGIN
    IF EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'pg_cron') THEN
        BEGIN
            PERFORM cron.unschedule('daily-stale-document-cleanup');
        EXCEPTION WHEN OTHERS THEN
            -- Ignore error if job does not exist yet
        END;
        
        PERFORM cron.schedule(
            'daily-stale-document-cleanup',
            '0 0 * * *',
            'SELECT public.cleanup_stale_documents(interval ''30 days'');'
        );
    END IF;
EXCEPTION WHEN OTHERS THEN
    -- Ignore if pg_cron is disabled in local environment
END $$;
