# Handoff Report — Survey 1: Database Architecture & pgvector / pg_cron Auto-Cleanup

## 1. Observation
- **Original Requirements**: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`, lines 27-29:
  > "### R4. Database & Auto-Cleanup (Supabase)
  > Configure Supabase with pgvector for vector storage. Implement a pg_cron scheduled job to automatically delete documents (and their chunks/files) that have not been queried in 30 days, unless marked 'keep_forever', to prevent hitting the 500MB database limit."
- **Embedding Model Alignment**: Voyage AI `voyage-3` and `voyage-3-lite` produce 1024-dimensional dense vectors.
- **pgvector Indexing Constraints**: HNSW (`vector_cosine_ops`) allows zero-shot index creation without requiring pre-warmed dataset clustering centroids (unlike IVFFlat which degrades or errors when initialized on empty tables).
- **Multi-Tenancy & Performance**: Denormalizing `user_id` onto `document_chunks` allows RLS policies and index filters to operate with zero SQL table joins during vector search.
- **Supabase Storage Integration**: Raw file objects are tracked in `storage.objects` under bucket `documents` with path pattern `{user_id}/{document_id}/{filename}`.

## 2. Logic Chain
1. *Step 1 (Quota calculation)*: Per Observation 1, the total database capacity limit is 500MB on Supabase free tier. A 1024-dimension float32 vector consumes 4,096 bytes. With an HNSW index overhead of ~1.6KB, chunk text of ~2KB, and relational metadata of ~400B, each chunk requires ~8KB of database storage. 500MB permits ~64,000 active chunks (~640 large RFP documents of 100 pages each).
2. *Step 2 (Indexing choice)*: Per Observation 3, HNSW provides superior recall (>98%) and low query latencies (<5ms) without a mandatory dataset training phase, making it optimal for dynamic document uploads.
3. *Step 3 (RLS & Tenancy)*: Per Observation 4, adding `user_id` to `document_chunks` enables single-table RLS checking (`auth.uid() = user_id`) and index acceleration via `(user_id, document_id, chunk_index)`.
4. *Step 4 (Auto-cleanup lifecycle)*: Using `pg_cron` scheduled at midnight (`0 0 * * *`), `cleanup_stale_documents(interval '30 days')` identifies documents where `keep_forever = false` and `COALESCE(last_queried_at, created_at) < now() - interval '30 days'`. It removes files from `storage.objects` and deletes records from `public.documents`, triggering cascade deletion to `public.document_chunks` and recording entries in `public.cleanup_audit_logs`.
5. *Step 5 (Query Activity Tracking)*: `touch_document_last_queried(uuid[])` updates `last_queried_at` whenever documents are matched during RAG queries, preventing active tenders from expiring.

## 3. Caveats
- `pg_cron` and `vector` extensions must be enabled in the Supabase project dashboard or via `CREATE EXTENSION` with appropriate superuser / admin permissions.
- In self-hosted or standard Supabase Cloud instances, deleting records from `storage.objects` via direct SQL removes metadata; if object storage hooks are disabled, physical bucket file pruning can also be coordinated via Supabase Storage API or Edge Functions.
- If Voyage AI `voyage-3-lite` is configured to output 512 dimensions instead of 1024 dimensions, the vector column must be adjusted from `vector(1024)` to `vector(512)` (defaulting to 1024 aligns with standard `voyage-3`).

## 4. Conclusion
The database architecture, DDL migration scripts, stored procedures (`match_documents`, `touch_document_last_queried`, `cleanup_stale_documents`), pg_cron schedule, and RLS policies are fully designed, documented, and delivered in `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_db/survey_report.md`.

## 5. Verification Method
1. Inspect the complete survey report and SQL migration script at `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_db/survey_report.md`.
2. When deploying to Supabase:
   - Run the SQL script `000_full_schema.sql` in the Supabase SQL Editor.
   - Verify extension installation: `SELECT * FROM pg_extension WHERE extname IN ('vector', 'pg_cron');`.
   - Verify table creation: `\d public.documents`, `\d public.document_chunks`.
   - Test vector search RPC: Call `SELECT * FROM public.match_documents(...)` with mock 1024-dim vector.
   - Verify cron registration: `SELECT * FROM cron.job WHERE jobname = 'daily-stale-document-cleanup';`.
   - Test cleanup dry-run: `SELECT public.cleanup_stale_documents(interval '0 days');`.
