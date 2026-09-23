# Original User Request

## 2026-08-27T12:02:39Z

# Teamwork Project Prompt — Draft

> Status: Launched
> Goal: Craft prompt → get user approval → delegate to teamwork_preview
> Requested team: [none — teamwork routes from the description]

Rebuild ApexTender v2.0 as a production-grade, free-tier-proof Retrieval-Augmented Generation (RAG) pipeline. 

Working directory: `/home/mohdfaizanali/Desktop/my projects/rfp-engine`
Integrity mode: development

## Requirements

### R1. Frontend UI (Next.js on Vercel)
Build a Next.js application that handles user authentication via Supabase Auth and allows users to upload documents directly to Supabase Storage. The frontend must communicate directly with the backend for queries to avoid Vercel's 10s serverless timeout.

### R2. Backend Engine (FastAPI on Render)
Build a lightweight Python FastAPI backend that strictly orchestrates API calls without performing heavy local compute (to survive Render's 512MB RAM limit). It must expose an endpoint to receive a query, call Voyage AI for embeddings, search Supabase pgvector, and stream an answer using Groq (Llama 3).

### R3. Document Processing (Supabase Edge Functions)
Implement Supabase Edge Functions triggered by Storage uploads. The function must send the file to LlamaParse (with a browser-side pdf.js fallback if the limit is hit), chunk the parsed text, call Voyage AI for embeddings, and store the vectors in Supabase pgvector.

### R4. Database & Auto-Cleanup (Supabase)
Configure Supabase with pgvector for vector storage. Implement a pg_cron scheduled job to automatically delete documents (and their chunks/files) that have not been queried in 30 days, unless marked "keep_forever", to prevent hitting the 500MB database limit.

## Acceptance Criteria

### Deployment & Limits
- [ ] Backend memory usage remains under 300MB during a query.
- [ ] Large file uploads (>10MB) succeed without hitting Vercel's 4.5MB body limit or crashing the backend.

### Functional
- [ ] User can authenticate, upload a document, and see it processed.
- [ ] User can ask a question and receive a streamed RAG response sourced from the uploaded document.
- [ ] The fallback parser successfully extracts text if LlamaParse fails or rate-limits.
- [ ] The auto-cleanup cron job successfully removes stale data when triggered.

## 2026-09-22T09:49:03Z

Working directory: /home/mohdfaizanali/Desktop/my projects/rfp-engine
Integrity mode: development

Remediate and harden ApexTender v2.0 / RFPANDA: align Groq LLM model identifiers across backend and frontend, replace fragile 65-second sleep loops in fallback ingestion with resilient backoff, preserve PDF page numbers and tables in chunking, eliminate blocking synchronous auth calls on FastAPI's async loop, and clean up workspace clutter.

## Requirements

### R1. Groq LLM Model Alignment & Model Switcher Hardening
Replace all occurrences of non-existent models (openai/gpt-oss-120b, openai/gpt-oss-20b, qwen/qwen3.8-27b, groq/compound) across the backend and frontend with valid production Groq model identifiers:
- Default model: llama-3.3-70b-versatile
- Fast fallback model: llama-3.1-8b-instant

Files to update:
- backend/app/config.py
- backend/app/schemas/query.py
- frontend/src/components/chat/ChatInterface.tsx
- frontend/src/lib/api-client.ts
- frontend/src/hooks/use-rag-query.ts

### R2. Fallback Ingestion Pipeline & Render Keep-Alive Repair
Refactor _process_fallback_ingestion_background in backend/app/routers/query.py:
1. Remove artificial throttling: Eliminate asyncio.sleep(65.0) and batch-size 4 throttling. Rely on Voyage client exponential backoff for 429 rate limits.
2. Add Root Health Route: In backend/app/main.py, add @app.get("/") returning {"status": "alive"} so keep-alive pings succeed with HTTP 200 instead of HTTP 404.
3. Re-ingestion Hygiene: Clean up previous chunks for document_id prior to inserting new chunks to prevent (document_id, chunk_index) UNIQUE constraint violations.
4. Metadata Synchronization: Update documents.metadata with total_chunks and total_tokens upon completion so the document library displays accurate counts.
5. Dead Code Elimination: Remove unreachable code and invalid _execute_write references.

### R3. Fallback Parser Citation & Chunking Precision
1. Page Delimiter Extraction: Update backend/app/services/chunker.py to recognize page markers (--- Page (\d+) --- and ## Page (\d+)) so chunks generated during fallback ingestion preserve their exact page_number in metadata.
2. Table Preservation: Enhance backend/app/services/chunker.py to detect Markdown tables (|) and prevent splitting rows across separate chunks.
3. Citation Validation: Ensure frontend citations link to the actual page number rather than defaulting to p. 1.

### R4. Non-Blocking Async Supabase Authentication Middleware
Refactor get_current_user in backend/app/auth.py:
1. Remove Client Allocation Overhead: Avoid creating a new create_client() instance on every request; pool a singleton client or reuse configuration.
2. Non-Blocking Execution: Ensure Supabase auth calls run without blocking FastAPI's ASGI event loop (using asyncio.to_thread or stateless HS256 JWT decoding via pyjwt with SUPABASE_JWT_SECRET).

### R5. Repository Hygiene & Clutter Removal
1. Remove all loose root patch scripts:
   - patch_backend.py
   - patch_incremental.py
   - patch_keepalive.py
   - fix_fallback.py
   - fix_fallback_url.py
   - fix_batch.py
   - fix_batch_again.py
   - fix_buttons.py
   - fix_syntax.py
   - fix_theme.py
   - rewrite_bubble.py
   - replace_theme.py
2. Remove the 343MB .rpm binary installer: code-1.138.0-1789458812.el8.x86_64 (1).rpm.

---

## Acceptance Criteria

### Functional & API Correctness
- [ ] POST /api/query successfully accepts queries specifying model: "llama-3.3-70b-versatile" and streams valid SSE events (sources, token, done).
- [ ] Frontend model switcher displays valid options: Llama 3.3 70B (Versatile) and Llama 3.1 8B (Instant).
- [ ] Fallback ingestion of a 20-page document completes in under 60 seconds without multi-minute sleeps.
- [ ] Chunks generated via fallback ingestion contain valid page_number values in metadata, correctly displayed in citation pills.
- [ ] The document library badge shows the actual total_chunks count instead of 0 chunks for fallback-processed documents.
- [ ] GET / returns HTTP 200 {"status": "alive"}.

### Performance & Memory Bounds
- [ ] FastAPI backend process RSS memory remains strictly < 300MB under query loads.
- [ ] Concurrent requests to get_current_user execute without blocking the ASGI event loop thread.

### Verification Suite
- [ ] All unit and integration tests pass: pytest backend/tests -v.
- [ ] E2E integration test suite passes: pytest tests/e2e -v.
- [ ] TypeScript typecheck passes with zero errors: npm run typecheck (or npx tsc --noEmit) in frontend.

## 2026-09-22T10:04:36Z

User Priority Update: The user requested to expedite execution immediately. Please direct the orchestrator to conclude Phase 0 immediately and dispatch M1, M2, M3, and M4 implementation workers concurrently to minimize completion time.
