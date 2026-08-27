## 2026-08-27T12:13:14Z

You are the Worker assigned to Milestone 2: Document Ingestion Pipeline (Supabase Edge Functions & Fallback Parser) for ApexTender v2.0.

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m2_edge`
Original request path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/ORIGINAL_REQUEST.md`
Project specification path: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/PROJECT.md`
Survey reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge/survey_report.md`
Schema reference: `/home/mohdfaizanali/Desktop/my projects/rfp-engine/supabase/migrations/20260827000000_initial_rag_schema.sql`

Your exclusive write ownership:
- `supabase/functions/` (all files within `supabase/functions/`)

Your tasks:
1. Read `ORIGINAL_REQUEST.md`, `PROJECT.md`, and the survey report at `.agents/explorer_survey_edge/survey_report.md`.
2. Implement the complete, production-grade Supabase Edge Functions in TypeScript / Deno:
   - `supabase/functions/_shared/chunker.ts`: Markdown-aware semantic chunker (500–1000 tokens, 100–150 token overlap) that preserves Markdown table rows (`| ... |`) and prepends section headers to maintain context.
   - `supabase/functions/_shared/voyage.ts`: REST API client for Voyage AI `voyage-3-lite` (1024d, `input_type: "document"`), batch size 64, retry with exponential backoff.
   - `supabase/functions/_shared/llamaparse.ts`: LlamaParse API client (file upload, job polling, markdown result extraction, and error classification: detects HTTP 429 rate limit, 402/403 quota exhaustion, or timeout).
   - `supabase/functions/_shared/supabase.ts`: Supabase client helper for Deno Edge Functions using service role or auth context.
   - `supabase/functions/_shared/cors.ts`: CORS headers for Edge Functions.
   - `supabase/functions/process-document/index.ts`: Edge Function handler for document ingestion:
     - Downloads file from Supabase Storage bucket `rfp-documents`.
     - Calls LlamaParse. If 429/402/timeout occurs, sets document status to `awaiting_fallback_parse` with error details in `metadata` and exits gracefully without crashing.
     - On successful parse, chunks markdown, calls Voyage AI for 1024d embeddings in batches, and inserts rows into `document_chunks` table, updating document status to `processed`.
   - `supabase/functions/ingest-fallback-text/index.ts`: Edge Function handler for fallback ingestion:
     - Receives `{ document_id, text, metadata }` sent by browser-side PDF.js.
     - Chunks text, calls Voyage AI for 1024d embeddings, inserts into `document_chunks`, and updates document status to `processed`.
3. Create comprehensive test scripts in `supabase/functions/tests/` verifying chunker logic, table preservation, Voyage AI batching, LlamaParse rate-limit handling, and fallback ingestion.
4. Run your verification tests and document commands, code layout, and results in `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/worker_m2_edge/handoff.md`.
5. Send a message to parent orchestrator when complete.
