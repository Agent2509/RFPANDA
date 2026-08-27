## 2026-08-27T12:06:40Z

You are the Worker assigned to Milestone 1: Database & pgvector Schema + pg_cron Auto-Cleanup for ApexTender v2.0.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m1_db`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`
Project specification path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`
DB Survey reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_db/survey_report.md`

Your exclusive write ownership:
- `supabase/migrations/20260827000000_initial_rag_schema.sql`
- `supabase/config.toml`
- `supabase/tests/` (schema validation and stored procedure SQL test scripts)

Your tasks:
1. Read `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`, `PROJECT.md`, and the survey report at `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_db/survey_report.md`.
2. Implement the complete, production-grade, idempotent SQL migration script at `supabase/migrations/20260827000000_initial_rag_schema.sql`:
   - Extensions: `vector`, `pg_cron`, `pgcrypto`, `pg_net` (with `IF NOT EXISTS`).
   - Tables:
     - `public.documents` (id, user_id, name, storage_path, file_size, mime_type, status, keep_forever, last_queried_at, created_at, updated_at, metadata).
     - `public.document_chunks` (id, document_id, user_id, chunk_index, content, embedding vector(1024), token_count, metadata, created_at).
     - `public.cleanup_audit_logs` (id, executed_at, documents_deleted_count, chunks_deleted_count, execution_duration_ms, details).
   - Constraints, Foreign Keys (cascade delete from documents to document_chunks).
   - Indexes:
     - HNSW index: `idx_document_chunks_embedding_hnsw ON public.document_chunks USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)`.
     - B-Tree indexes on `documents(user_id)`, `documents(last_queried_at)`, `documents(keep_forever)`, `documents(status)`, `document_chunks(document_id)`, `document_chunks(user_id)`.
   - Row Level Security (RLS) enabled on all tables with policies for authenticated users (`auth.uid() = user_id`) and service role (`service_role`).
   - Stored Procedure `match_documents` with cosine distance `<=>`, filtering by user_id and optional document_id.
   - Stored Procedure `touch_document_last_queried` updating `last_queried_at = now()`.
   - Stored Procedure `cleanup_stale_documents(retention_interval interval DEFAULT interval '30 days')` deleting unqueried documents where `keep_forever = false` and older than retention period, recording metrics in `cleanup_audit_logs`.
   - `pg_cron` schedule `daily-stale-document-cleanup` scheduled at `0 0 * * *`.
3. Create `supabase/config.toml` configuring Supabase local development, storage bucket `rfp-documents`, and db settings.
4. Create test/verification SQL scripts in `supabase/tests/` to validate:
   - Table and column types.
   - Vector insertion and `match_documents` similarity search.
   - Cascade deletion.
   - `touch_document_last_queried` execution.
   - `cleanup_stale_documents` execution and audit logging.
5. Execute verification commands (e.g. running test scripts or validating SQL syntax) and document all results in `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m1_db/handoff.md`.
6. Send a message to parent orchestrator when complete.
