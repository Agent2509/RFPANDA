## 2026-08-27T12:04:05Z
You are an Explorer / Specification Specialist assigned to Survey 1: Database Architecture & pgvector / pg_cron Auto-cleanup.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_db`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`

Your tasks:
1. Read `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`.
2. Investigate and specify the complete Supabase PostgreSQL schema needed for ApexTender v2.0:
   - Extensions: `vector` (pgvector), `pg_cron`, `uuid-ossp` or `pgcrypto`.
   - Tables: `documents` (id, user_id, name, storage_path, file_size, mime_type, status, keep_forever boolean, last_queried_at timestamp, created_at timestamp, metadata jsonb), `document_chunks` (id, document_id, chunk_index, content text, embedding vector(1024) [or compatible with Voyage AI voyage-3 / voyage-3-lite], token_count int, metadata jsonb, created_at timestamp).
   - Indexes: HNSW / IVFFlat cosine similarity index on `embedding`, indexes on user_id, document_id, last_queried_at, keep_forever.
   - Row Level Security (RLS) policies: Secure documents and chunks so users can only view/manage their own data, while service role / edge functions have necessary access.
   - Stored Procedure / RPC function: `match_documents` for vector similarity search (taking query_embedding, match_threshold, match_count, filter_user_id, optional document_id filter).
   - Auto-Cleanup Cron: `pg_cron` schedule (e.g. daily at midnight) executing a cleanup function to delete documents (and cascading chunks + storage objects) where `keep_forever = false` and `last_queried_at < now() - interval '30 days'` (or created_at if last_queried_at is null). Include proper cascade/storage deletion strategy.
   - Stored Procedure for `touch_document_last_queried` when a query searches document chunks.
3. Write your detailed findings, SQL migration scripts, function signatures, and recommendations to `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_db/survey_report.md` and write a soft `handoff.md`.
4. When finished, send a message to your parent orchestrator summarizing your findings and linking to your reports.
