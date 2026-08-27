# BRIEFING — 2026-08-27T12:06:00Z

## Mission
Survey, architect, and specify the Supabase Edge Functions and Document Ingestion Pipeline for ApexTender v2.0, including Storage bucket setup, webhook/function triggers, LlamaParse parsing with PDF.js fallback, recursive semantic chunking, Voyage AI batched embeddings, Supabase pgvector chunk insertion, security, and free-tier optimization.

## 🔒 My Identity
- Archetype: Explorer / Specialist
- Roles: Edge Functions & Document Ingestion Pipeline Specialist
- Working directory: /home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge
- Original parent: becaab28-d2b0-4598-9ff0-d4df3c56e0a7
- Milestone: Survey 2: Supabase Edge Functions & Document Ingestion Pipeline

## 🔒 Key Constraints
- Read-only investigation — do NOT implement production app code directly during survey phase.
- Write ONLY to `.agents/explorer_survey_edge/` folder.
- All communications to parent orchestrator must be sent via `send_message` to recipient `becaab28-d2b0-4598-9ff0-d4df3c56e0a7`.
- Deliver comprehensive specification report at `.agents/explorer_survey_edge/survey_report.md` and handoff at `.agents/explorer_survey_edge/handoff.md`.

## Current Parent
- Conversation ID: becaab28-d2b0-4598-9ff0-d4df3c56e0a7
- Updated: 2026-08-27T12:06:00Z

## Investigation State
- **Explored paths**: `ORIGINAL_REQUEST.md`, `.agents/explorer_survey_db/BRIEFING.md`, `.agents/orchestrator_1/BRIEFING.md`, `.agents/explorer_survey_app/DISPATCH.md`
- **Key findings**:
  - Direct browser upload to Supabase Storage `rfp-documents` bypasses Vercel 4.5MB limit.
  - Dual-tier parser architecture: LlamaParse cloud parser with automatic fallback to browser-side `pdfjs-dist` on HTTP 429/402 or timeout.
  - Custom markdown-aware semantic chunker that preserves table structures (`| ... |`) and prepends section context to each 500-1000 token chunk.
  - Voyage AI client using `voyage-3-lite` (1024-dim) in batches of 64 chunks with exponential backoff.
  - Edge Function endpoints: `process-document` (main) and `ingest-fallback-text` (fallback text ingestion).
- **Unexplored areas**: None. Full specification, data contracts, and complete Deno implementation code templates produced in report.

## Key Decisions Made
- Use Deno runtime standard for Supabase Edge Functions with `@supabase/supabase-js`.
- Use Voyage AI `voyage-3-lite` (1024-dim) for high-speed, cost-effective embeddings.
- Implement two Edge Functions:
  1. `process-document`: Handles direct post-upload / database webhook trigger, calls LlamaParse, chunks text, generates embeddings, stores chunks in DB.
  2. `ingest-fallback-text`: Receives pre-parsed raw/markdown text from client-side PDF.js (when LlamaParse rate-limits or fails), executes chunking and Voyage AI embeddings.
- Store file in Storage as `{user_id}/{document_id}/{filename}` with strict RLS policies.

## Artifact Index
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge/survey_report.md` — Complete Survey Report and Ingestion Specs
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge/handoff.md` — 5-component handoff report
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge/progress.md` — Progress tracker and liveness heartbeat
- `/home/mohdfaizanali/Desktop/my projects/rfp-engine/.agents/explorer_survey_edge/DISPATCH.md` — Dispatch log
